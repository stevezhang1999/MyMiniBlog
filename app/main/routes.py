from flask import render_template, flash, redirect, url_for, request
from werkzeug.urls import url_parse
from flask import current_app, g

from app import db
from app.main.forms import EditProfileForm, PostForm, SearchForm, MessageForm
from app.models import User, Post, Message

from flask_login import current_user, login_user
from flask_login import logout_user
from flask_login import login_required

from datetime import datetime

from app.main import bp

@bp.before_request
def before_request():
    if current_user:
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
            g.search_form = SearchForm()

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your post is now live!")
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, int)
    posts = current_user.followed_posts().paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None

    return render_template('index.html', title='Home', posts=posts.items, 
                            form=form, next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    page = request.args.get('page', 1, int)
    user = User.query.filter_by(username=username).first()
    posts = user.posts.paginate(page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.user', username=username, page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                            next_url=next_url, prev_url=prev_url)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved')
        return redirect(url_for('main.edit_profile'))
    elif request.method=='GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot follow yourself.')
        return redirect(url_for('main.index'))
    
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('main.index'))

@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot unfollow yourself.')
        return redirect(url_for('main.index'))
    
    current_user.unfollow(user)
    db.session.commit()
    flash('You unfollowed {}.'.format(username))
    return redirect(url_for('main.index'))

@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page, current_app._get_current_object().config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items,
                            next_url=next_url, prev_url=prev_url)

@bp.route('/search')
@login_required
def search():
    flash("validate {}".format(g.search_form.validate()) )
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    flash("validate {}".format(g.search_form.validate()) )

    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data,  page=page, 
                                    per_page=current_app.config['POSTS_PER_PAGE'])

    next_url = url_for('main.search', q=g.search_form.q.data, page=page+1) \
        if page * current_app.config['POSTS_PER_PAGE'] < total else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page-1) \
        if page > 1 else None

    return render_template(
        'search.html',
        title='Search',
        posts=posts,
        next_url=next_url,
        prev_url=prev_url
    )

@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    db.session.commit()

    page = request.args.get('page', 1, int)
    msgs = current_user.messages_received.order_by(Message.timestamp.desc()).paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.messages', page=msgs.next_num) \
        if msgs.has_next else None
    prev_url = url_for('main.messages', page=msgs.prev_num) \
        if msgs.has_prev else None
    return render_template('messages.html', title='Messages', messages=msgs.items,
                            next_url=next_url, prev_url=prev_url)

@bp.route('/send_message/<recipient_name>', methods=['GET', 'POST'])
@login_required
def send_message(recipient_name):
    form = MessageForm()
    if form.validate_on_submit():
        recipient = User.query.filter_by(username=recipient_name).first_or_404()
        new_msg = Message(author=current_user, recipient=recipient, body=form.message.data)
        db.session.add(new_msg)
        db.session.commit()

        flash('Message sent successfully')
        return redirect(url_for('main.user', username=recipient_name))
    return render_template('send_message.html', title='Send message', form=form, recipient=recipient_name)