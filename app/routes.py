"""
Application Layer - Routes
HTTP request handlers and view controllers
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from email_validator import validate_email, EmailNotValidError
import random
import os
import resend
from app.services import CodeAnalysisService, CodeValidationService
from app.models import User, CodeSubmission, ReviewHistory
from app.extensions import db, mail, limiter
from config import Config
from datetime import datetime, timedelta


def register_routes(app):
    """
    Register all application routes
    Called from app factory
    """
    
    @app.route('/')
    def index():
        """
        Home page - Redirects to new React Frontend
        """
        return redirect("http://localhost:5173/")
    
    # ==================== AUTHENTICATION ROUTES ====================
    
    # LEGACY FLASK HTML FRONTEND HAS BEEN REMOVED
    # All users must now access the new React app at http://localhost:5173
    
    # ==================== API AUTHENTICATION ROUTES ====================
    
    def generate_otp():
        return ''.join(random.choices('0123456789', k=6))

    def send_otp_email(user_email, otp):
        html_body = f"""
        <div style="font-family: Arial, sans-serif; text-align: center; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
            <h2 style="color: #10b981;">Verify Your Email</h2>
            <p>Welcome to CodeReview.ai! Please use the following One-Time Password to verify your account.</p>
            <h1 style="font-size: 36px; letter-spacing: 5px; color: #333; background: #f3f4f6; padding: 15px; border-radius: 8px;">{otp}</h1>
            <p style="color: #666; font-size: 14px;">This OTP expires in 10 minutes.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">If you didn't request this, please ignore this email.</p>
        </div>
        """
        
        provider = app.config.get('MAIL_PROVIDER', 'gmail').lower()
        
        # Helper for Resend
        def send_via_resend():
            if not app.config.get('RESEND_API_KEY') or app.config.get('RESEND_API_KEY') == 're_your_api_key_here':
                raise Exception("Resend API key not configured")
                
            resend.api_key = app.config.get('RESEND_API_KEY')
            params = {
                "from": "CodeReview.ai <onboarding@resend.dev>",
                "to": [user_email],
                "subject": "Verify Your Email - CodeReview.ai",
                "html": html_body
            }
            resend.Emails.send(params)
            app.logger.info("Successfully sent email via Resend API.")

        # Helper for Gmail
        def send_via_gmail():
            msg = Message("Verify Your Email - CodeReview.ai",
                          recipients=[user_email],
                          html=html_body)
            # Dotenv Deep Debugging
            app.logger.info("--- GMAIL DOTENV DEBUG ---")
            app.logger.info(f"MAIL_PASSWORD repr(): {repr(os.getenv('MAIL_PASSWORD'))}")
            app.logger.info("--------------------------")
            mail.send(msg)
            app.logger.info("Successfully sent email via Gmail SMTP.")

        if provider == 'resend':
            send_via_resend()
        else:
            # Default to Gmail, with failover to Resend
            try:
                send_via_gmail()
            except Exception as e:
                app.logger.error(f"Gmail SMTP Failed: {e}")
                app.logger.info("Attempting automatic failover to Resend API...")
                try:
                    send_via_resend()
                except Exception as resend_e:
                    app.logger.error(f"Resend Fallback Failed: {resend_e}")
                    raise Exception(f"Both Gmail and Resend failed. Gmail error: {e}")
    
    @app.route('/api/signup', methods=['POST'])
    @limiter.limit("5 per minute")
    def api_signup():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Missing JSON data'}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
            
        # Validate Email and check MX
        try:
            valid = validate_email(email, check_deliverability=True)
            email = valid.normalized
        except EmailNotValidError as e:
            return jsonify({'success': False, 'message': str(e)}), 400
            
        if User.query.filter_by(email=email).first():
            # Prevent enumeration - generic error
            return jsonify({'success': False, 'message': 'Email already registered or invalid'}), 400
            
        user = User(username=email, email=email, full_name=email.split('@')[0], is_verified=False)
        user.set_password(password)
        
        # Generate OTP
        otp = generate_otp()
        user.otp_hash = generate_password_hash(otp)
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        user.otp_attempts = 0
        user.last_otp_sent = datetime.utcnow()
        
        db.session.add(user)
        db.session.commit()
        
        app.logger.info(f"==== DEVELOPMENT OTP FOR {user.email}: {otp} ====")
        try:
            send_otp_email(user.email, otp)
        except Exception as e:
            app.logger.error(f"Failed to send email: {e}")
            app.logger.warning("Proceeding without sending email (Check console for OTP).")
            # We don't return 500 here so the user can test the UI using the printed OTP
        
        return jsonify({
            'success': True,
            'requires_verification': True,
            'message': 'OTP sent to email (or console if SMTP failed)'
        })

    @app.route('/api/verify-email', methods=['POST'])
    @limiter.limit("10 per minute")
    def api_verify_email():
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return jsonify({'success': False, 'message': 'Email and OTP required'}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 400
            
        if user.is_verified:
            return jsonify({'success': False, 'message': 'Account already verified'}), 400
            
        if user.otp_locked_until and user.otp_locked_until > datetime.utcnow():
            return jsonify({'success': False, 'message': 'Account temporarily locked. Please try again later.'}), 403
            
        if user.otp_expiry < datetime.utcnow():
            return jsonify({'success': False, 'message': 'OTP expired'}), 400
            
        if not check_password_hash(user.otp_hash, otp):
            user.otp_attempts += 1
            if user.otp_attempts >= 5:
                user.otp_locked_until = datetime.utcnow() + timedelta(minutes=15)
                db.session.commit()
                return jsonify({'success': False, 'message': 'Too many failed attempts. Account locked for 15 minutes.'}), 403
            db.session.commit()
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
            
        # Success
        user.is_verified = True
        user.otp_hash = None
        user.otp_attempts = 0
        db.session.commit()
        
        login_user(user, remember=True)
        user.update_last_login()
        token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {'id': user.id, 'email': user.email, 'username': user.username}
        })

    @app.route('/api/resend-otp', methods=['POST'])
    @limiter.limit("5 per minute")
    def api_resend_otp():
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email required'}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user or user.is_verified:
            return jsonify({'success': True, 'message': 'If the email exists and is unverified, an OTP has been sent.'})
            
        if user.last_otp_sent and (datetime.utcnow() - user.last_otp_sent).total_seconds() < 60:
            return jsonify({'success': False, 'message': 'Please wait 60 seconds before requesting a new OTP.'}), 429
            
        otp = generate_otp()
        user.otp_hash = generate_password_hash(otp)
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        user.otp_attempts = 0
        user.last_otp_sent = datetime.utcnow()
        db.session.commit()
        
        app.logger.info(f"==== DEVELOPMENT RESEND OTP FOR {user.email}: {otp} ====")
        try:
            send_otp_email(user.email, otp)
        except Exception as e:
            app.logger.error(f"Failed to send email: {e}")
            app.logger.warning("Proceeding without sending email (Check console for OTP).")
            
        return jsonify({'success': True, 'message': 'OTP sent (or check console if SMTP failed)'})

    @app.route('/api/login', methods=['POST'])
    @limiter.limit("10 per minute")
    def api_login():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Missing JSON data'}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.check_password(password):
            if user:
                user.failed_login_attempts += 1
                db.session.commit()
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            
        if not user.is_verified:
            return jsonify({'success': False, 'requires_verification': True, 'message': 'Please verify your email first'}), 403
            
        # Reset failed attempts on success
        user.failed_login_attempts = 0
        login_user(user, remember=True)
        user.update_last_login()
        
        token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {'id': user.id, 'email': user.email, 'username': user.username}
        })
        
    @app.route('/api/logout', methods=['POST'])
    def api_logout():
        logout_user()
        return jsonify({'success': True, 'message': 'Logged out'})
        
    @app.route('/api/session', methods=['GET'])
    def api_session():
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True,
                'user': {'id': current_user.id, 'email': current_user.email, 'username': current_user.username}
            })
        return jsonify({'authenticated': False}), 401
    
    @app.route('/api/history', methods=['GET'])
    @jwt_required()
    def api_history():
        """
        REST API endpoint to fetch user's review history
        """
        user_id = int(get_jwt_identity())
        # Get user's reviews
        reviews = ReviewHistory.query.filter_by(user_id=user_id)\
            .order_by(ReviewHistory.created_at.desc()).all()
            
        history_data = []
        for review in reviews:
            submission = CodeSubmission.query.get(review.code_submission_id)
            code_snippet = ""
            if submission and submission.code_text:
                code_snippet = submission.code_text
            
            # Format score dynamically
            score_val = 10.0
            if review.issues_found:
                score_val = max(1.0, 10.0 - (review.issues_found * 0.5))
                
            history_data.append({
                'id': str(review.id),
                'language': review.language or 'python',
                'score': f"{score_val:.1f}",
                'codeSnippet': code_snippet,
                'date': review.created_at.isoformat() + 'Z'
            })
            
        return jsonify({
            'success': True,
            'history': history_data
        })
        
    @app.route('/api/history/<int:review_id>', methods=['DELETE'])
    @jwt_required()
    def delete_history(review_id):
        user_id = int(get_jwt_identity())
        review = ReviewHistory.query.filter_by(id=review_id, user_id=user_id).first()
        if not review:
            return jsonify({'success': False, 'message': 'History not found or unauthorized'}), 404
            
        try:
            db.session.delete(review)
            db.session.commit()
            return jsonify({'success': True, 'message': 'History deleted'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # ==================== ANALYSIS ROUTES ====================
    

    
    # ==================== UTILITY ROUTES ====================
    
    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        """
        REST API endpoint for AI Chatbox routing engine
        """
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt parameter'}), 400
            
        import hashlib
        import uuid
        
        # 1. Immutable Context Snapshot creation
        request_id = str(uuid.uuid4())
        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        code_baseline = data.get("code", "")
        baseline_hash = hashlib.sha256(code_baseline.encode('utf-8')).hexdigest()
        
        data["metadata"] = {
            "request_id": request_id,
            "snapshot_id": snapshot_id,
            "baseline_hash": baseline_hash,
            "semantic_engine_version": "v1.4.2",
            "policy_version": "v2.3.0",
            "prompt_template_version": "v3.1",
            "token_budget_profile": "strict-fractional-v1"
        }
            
        from app.analyzer.chat_engine import ChatEngine
        engine = ChatEngine()
        
        # We use standard JSON response since SSE generation with strict schema is complex 
        # for a first iteration. Wait for completion and return final response.
        try:
            response = engine.generate_chat_response(data)
            # Inject metadata back to frontend
            response["_metadata"] = data["metadata"]
            return jsonify(response)
        except Exception as e:
            app.logger.error(f"Chat Engine Error [{request_id}]: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analyze', methods=['POST'])
    def api_analyze():
        """
        REST API endpoint for code analysis
        Returns JSON response
        """
        data = request.get_json()
        
        if not data or 'code' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing code parameter',
                'time_complexity': 'O(1)',
                'space_complexity': 'O(1)'
            }), 400
        
        code = data['code']
        language = data.get('language', 'python')
        
        # Validate
        validation = CodeValidationService.validate_code(code, Config.MAX_CODE_LENGTH)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'error': {
                    'message': validation['error'],
                    'code': 'VALIDATION_FAILURE',
                    'recoverable': False,
                    'severity': 'info'
                },
                'time_complexity': 'O(1)',
                'space_complexity': 'O(1)'
            }), 400
        
        # Analyze
        service = CodeAnalysisService(code, language)
        results = service.analyze()
        
        if not results['success']:
            status_code = 400 if results.get('stage') == 'parsing' else 500
            return jsonify(results), status_code
        
        # Save to database (with user if authenticated)
        try:
            user_id = current_user.id if current_user.is_authenticated else None
            submission = service.save_to_database(user_id=user_id)
            submission.status = 'reviewed'
            results['submission_id'] = submission.id
            
            # Save review history if user is logged in
            if current_user.is_authenticated:
                issues_count = len(results.get('issues', []))
                ai_text = results.get('ai_suggestions', '')
                import json
                if isinstance(ai_text, dict):
                    ai_text = json.dumps(ai_text)
                elif isinstance(ai_text, list):
                    ai_text = '\n'.join(ai_text)
                
                review = ReviewHistory(
                    user_id=user_id,
                    code_submission_id=submission.id,
                    review_result=ai_text,
                    language=language,
                    issues_found=issues_count,
                    complexity_score=str(submission.complexity_score) if submission.complexity_score else 'N/A'
                )
                db.session.add(review)
            
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Database save failed: {e}")
            db.session.rollback()
        
        return jsonify(results)
    
    # ==================== UTILITY ROUTES ====================
    
    @app.route('/health')
    def health():
        """
        Health check endpoint
        """
        return jsonify({
            'status': 'healthy',
            'service': 'AI Code Review Assistant'
        })
    
    @app.errorhandler(404)
    def not_found(error):
        """404 error handler"""
        return jsonify({'success': False, 'message': 'Route not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """500 error handler"""
        app.logger.error(f"Server error: {error}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500