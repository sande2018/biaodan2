from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db, login
from app.models import Form, FormField, FormSubmission, CDK, User
from flask_login import login_user, logout_user, current_user, login_required
import uuid
import json
from datetime import datetime

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('用户名或密码错误', 'error')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('admin_dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    forms = Form.query.all()
    return render_template('admin/dashboard.html', forms=forms)

@app.route('/admin/form/create', methods=['GET', 'POST'])
@login_required
def create_form():
    if request.method == 'POST':
        form_name = request.form['form_name']
        form_slug = request.form['form_slug']
        description = request.form['description']
        is_active = request.form.get('is_active') == 'on'
        cdk_enabled = request.form.get('cdk_enabled') == 'on'
        cdk_stock = int(request.form['cdk_stock']) if request.form['cdk_stock'] else 0
        cdk_description = request.form['cdk_description']
        cdk_popup = request.form.get('cdk_popup') == 'on'
        ip_limit = int(request.form['ip_limit']) if request.form['ip_limit'] else 0
        
        # 创建表单
        form = Form(
            name=form_name,
            slug=form_slug,
            description=description,
            is_active=is_active,
            cdk_enabled=cdk_enabled,
            cdk_stock=cdk_stock,
            cdk_description=cdk_description,
            cdk_popup=cdk_popup,
            ip_limit=ip_limit
        )
        db.session.add(form)
        db.session.commit()
        
        flash('表单创建成功！', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/create_form.html')

@app.route('/form/<slug>', methods=['GET', 'POST'])
def fill_form(slug):
    form = Form.query.filter_by(slug=slug, is_active=True).first_or_404()
    fields = FormField.query.filter_by(form_id=form.id).order_by(FormField.order).all()
    
    if request.method == 'POST':
        # 获取用户IP和设备信息
        ip_address = request.remote_addr
        user_agent = request.user_agent.string
        
        # 检查IP限制
        if form.ip_limit > 0:
            submission_count = FormSubmission.query.filter_by(form_id=form.id, ip_address=ip_address).count()
            if submission_count >= form.ip_limit:
                flash('您已达到该表单的提交限制！', 'error')
                return render_template('fill_form.html', form=form, fields=fields)
        
        # 表单验证
        form_data = {}
        validation_passed = True
        
        for field in fields:
            if field.type == 'checkbox':
                field_value = request.form.getlist(field.name)
            else:
                field_value = request.form.get(field.name, '')
            
            form_data[field.name] = field_value
            
            # 应用验证规则
            if field.validation_rules:
                rules = field.validation_rules
                
                # 必填验证
                if field.required and not field_value:
                    flash(f'请填写{field.label}', 'error')
                    validation_passed = False
                    continue
                
                # 最小长度验证
                if 'min_length' in rules and len(field_value) < rules['min_length']:
                    flash(f'{field.label}长度不能少于{rules["min_length"]}个字符', 'error')
                    validation_passed = False
                    continue
                
                # 最大长度验证
                if 'max_length' in rules and len(field_value) > rules['max_length']:
                    flash(f'{field.label}长度不能超过{rules["max_length"]}个字符', 'error')
                    validation_passed = False
                    continue
                
                # 邮箱格式验证
                if field.type == 'email' and field_value:
                    import re
                    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
                    if not re.match(email_regex, field_value):
                        flash(f'{field.label}格式不正确', 'error')
                        validation_passed = False
                        continue
        
        if not validation_passed:
            return render_template('fill_form.html', form=form, fields=fields)
        for field in fields:
            if field.type == 'checkbox':
                form_data[field.name] = request.form.getlist(field.name)
            else:
                form_data[field.name] = request.form.get(field.name, '')
        
        # 分配CDK
        assigned_cdk = None
        if form.cdk_enabled and form.cdk_stock > 0:
            cdk = CDK.query.filter_by(form_id=form.id, is_used=False).first()
            if cdk:
                cdk.is_used = True
                cdk.used_at = datetime.utcnow()
                form.cdk_stock -= 1
                assigned_cdk = cdk
        
        # 创建提交记录
        submission = FormSubmission(
            form_id=form.id,
            data=form_data,
            ip_address=ip_address,
            user_agent=user_agent,
            cdk_id=assigned_cdk.id if assigned_cdk else None
        )
        
        db.session.add(submission)
        db.session.commit()
        
        flash('表单提交成功！', 'success')
        return render_template('submission_success.html', form=form, cdk=assigned_cdk)
    
    return render_template('fill_form.html', form=form, fields=fields)

@app.route('/api/form/<slug>/fields')
def get_form_fields(slug):
    form = Form.query.filter_by(slug=slug, is_active=True).first_or_404()
    fields = FormField.query.filter_by(form_id=form.id).order_by(FormField.order).all()
    
    fields_data = []
    for field in fields:
        fields_data.append({
            'id': field.id,
            'name': field.name,
            'label': field.label,
            'type': field.type,
            'required': field.required,
            'options': field.options,
            'placeholder': field.placeholder,
            'order': field.order
        })
    
    return jsonify({'fields': fields_data})

@app.route('/admin/form/<int:form_id>/fields', methods=['GET', 'POST'])
@login_required
def manage_form_fields(form_id):
    form = Form.query.get_or_404(form_id)
    
    if request.method == 'POST':
        # 处理字段创建
        field_name = request.form['field_name']
        field_label = request.form['field_label']
        field_type = request.form['field_type']
        field_required = request.form.get('field_required') == 'on'
        field_placeholder = request.form['field_placeholder']
        field_order = int(request.form['field_order'])
        
        # 处理选项
        options = None
        if field_type in ['select', 'radio', 'checkbox']:
            options_text = request.form['field_options']
            options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
        
        # 处理验证规则
        validation_rules = None
        if request.form['validation_rules']:
            validation_rules = json.loads(request.form['validation_rules'])
        
        # 创建字段
        field = FormField(
            form_id=form.id,
            name=field_name,
            label=field_label,
            type=field_type,
            required=field_required,
            options=options,
            placeholder=field_placeholder,
            order=field_order,
            validation_rules=validation_rules
        )
        
        db.session.add(field)
        db.session.commit()
        flash('字段添加成功！', 'success')
        return redirect(url_for('manage_form_fields', form_id=form.id))
    
    fields = FormField.query.filter_by(form_id=form.id).order_by(FormField.order).all()
    return render_template('admin/manage_fields.html', form=form, fields=fields)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/admin/form/<int:form_id>/submissions')
@login_required
def view_submissions(form_id):
    form = Form.query.get_or_404(form_id)
    submissions = FormSubmission.query.filter_by(form_id=form.id).order_by(FormSubmission.created_at.desc()).all()
    return render_template('admin/view_submissions.html', form=form, submissions=submissions)

@app.route('/admin/field/<int:field_id>/delete', methods=['POST'])
@login_required
def delete_field(field_id):
    field = FormField.query.get_or_404(field_id)
    form_id = field.form_id
    db.session.delete(field)
    db.session.commit()
    flash('字段删除成功！', 'success')
    return redirect(url_for('manage_form_fields', form_id=form_id))

@app.route('/admin/form/<int:form_id>/delete', methods=['POST'])
@login_required
def delete_form(form_id):
    form = Form.query.get_or_404(form_id)
    db.session.delete(form)
    db.session.commit()
    flash('表单删除成功！', 'success')
    return redirect(url_for('admin_dashboard'))

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
