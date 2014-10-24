#This file is part newsletter blueprint for Flask.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from flask import Blueprint, request, render_template, flash, current_app, \
    redirect, url_for, g
from flask.ext.babel import gettext as _
from flask.ext.wtf import Form
from wtforms import TextField, validators
from flask.ext.mail import Mail, Message
from galatea.tryton import tryton
from trytond.transaction import Transaction

newsletter = Blueprint('newsletter', __name__, template_folder='templates')

NEWSLETTER_LISTS = current_app.config.get('TRYTON_NEWSLETTER_LISTS', [])
NEWSLETTER_EMAIL = current_app.config.get('TRYTON_NEWSLETTER_EMAIL_SUBSCRIBER', False)

NewsletterContact = tryton.pool.get('newsletter.contact')


class NewsletterForm(Form):
    "Newsletter form"
    name = TextField(_('Name'))
    email = TextField(_('Email'), [validators.Required(), validators.Email()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False
        return True

    def reset(self):
        self.name.data = ''
        self.email.data = ''

def send_email(data):
    """
    Send an newsletter email
    :param data: dict
    """
    mail = Mail(current_app)

    subject = '%s %s' % (
        _('Welcome newsletter'),
        current_app.config.get('TITLE'),
        )
    email = current_app.config.get('DEFAULT_MAIL_SENDER')

    msg = Message(subject,
            body = render_template('emails/newsletter-text.jinja', data=data),
            html = render_template('emails/newsletter-html.jinja', data=data),
            sender = email,
            recipients = [email, data.get('email')])
    mail.send(msg)

@newsletter.route("/unsubscriber", methods=["GET", "POST"],
    endpoint="unsubscriber")
@tryton.transaction()
def unsubscriber(lang):
    '''Unsubscription all newsletters'''
    email = request.form.get('email', None)

    form = NewsletterForm()
    if form.validate_on_submit():
        with Transaction().set_context(active_test=False):
            contacts = NewsletterContact.search([
                ('email', '=', email),
                ], limit=1)

        if contacts:
            NewsletterContact.write(contacts, {'active': False})
            flash(_('Unsubscribed %s in our newsletter!' % email))
        else:
            flash(_('Your email %s not found in our newsletter!' % email))

    if email and not form.validate_on_submit():
        flash(_('Email is not valid!'), 'danger')

    form.reset()
    return render_template('newsletter-unsubscriber.html', form=form)

@newsletter.route("/subscriber", methods=["GET", "POST"], endpoint="subscriber")
@tryton.transaction()
def subscriber(lang):
    '''Subscription'''
    name = request.form.get('name', None)
    email = request.form.get('email', None)
    
    form = NewsletterForm()
    if form.validate_on_submit():
        data = {
            'email': email,
            'active': True,
            }
        if name:
            data['name'] = name

        contact = None
        with Transaction().set_context(active_test=False):
            contacts = NewsletterContact.search([
                ('email', '=', email),
                ], limit=1)
        if contacts:
            contact, = contacts

        if contact:
            add_list = []
            if NEWSLETTER_LISTS:
                current_lists = [l.id for l in contact.lists]
                for l in NEWSLETTER_LISTS:
                    if l not in current_lists:
                        add_list.append(l)
            if add_list:
                data['lists'] = [['add', add_list]]
                flash(_('Updated your email in our newsletter!'))
            else:
                flash(_('Your email is already in our newsletter!'))
            NewsletterContact.write([contact], data)
        else:
            if NEWSLETTER_LISTS:
                data['lists'] = [['add', NEWSLETTER_LISTS]]
            NewsletterContact.create([data])

            flash(_('Thanks! Your subscription was submitted successfully!'))

            if NEWSLETTER_EMAIL:
                send_email(data)

    if email and not form.validate_on_submit():
        flash(_('Email is not valid!'), 'danger')

    form.reset()
    return render_template('newsletter-subscriber.html', form=form)

@newsletter.route("/", endpoint="news")
def news(lang):
    '''Redirect to subcription'''
    return redirect(url_for('.subscriber', lang=g.language))
