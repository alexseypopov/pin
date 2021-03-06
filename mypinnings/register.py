import random
import json
import calendar
import datetime
import os.path
from gettext import gettext as _

import web

from mypinnings import auth
from mypinnings import template
from mypinnings import session
from mypinnings import database
from mypinnings import cached_models
from mypinnings.conf import settings


urls = ('/after-signup/(\d*)', 'PageAfterSignup',
        '/after-signup', 'PageAfterSignup',
        '/api/users/me/category/(\d*)/?', 'ApiRegisterCategoryForUser',
        '/api/users/me/coolpins/(\d*)/?', 'ApiRegisterCoolPinForUser',
        '', 'PageRegister',
        )


valid_email = web.form.regexp(r"[^@]+@[^@]+\.[^@]+", "Must be a valid email address")


class PageRegister:
    if not hasattr(settings, 'LANGUAGES') or not settings.LANGUAGES:
        languages = (('en', 'English'),)
    else:
        languages = settings.LANGUAGES
    _form = web.form.Form(
        web.form.Textbox('username', web.form.notnull, id='username', autocomplete='off'),
        web.form.Textbox('name', web.form.notnull, autocomplete='off',
                         description="Complete name"),
        web.form.Textbox('email', valid_email, web.form.notnull, autocomplete='off', id='email'),
        web.form.Password('password', web.form.notnull, id='password', autocomplete='off'),
        web.form.Dropdown('language', languages, web.form.notnull),
        web.form.Button('Let\'s get started!')
    )

    def msg(self, s):
        raise web.seeother('?msg=%s' % s, absolute=False)

    def GET(self):
        form = self._form()
        message = web.input(msg=None).msg
        if message:
            return template.tpl('register/reg', form, message)
        return template.tpl('register/reg', form)

    def POST(self):
        form = self._form()
        if form.validates():
            if auth.email_exists(form.d.email):
                self.msg('Sorry, that email already exists.')

            if auth.username_exists(form.d.username):
                self.msg('Sorry, that username already exists.')

            activation = random.randint(1, 10000)
            hashed = hash(str(activation))

            user_id = auth.create_user(form.d.email, form.d.password, name=form.d.name, username=form.d.username, activation=activation,
                                       locale=form.d.language)
            if not user_id:
                msg = _('Sorry, a database error occurred and we couldn\'t create your account.')
                return template.tpl('register/reg', form, msg)
            send_activation_email(form.d.email, hashed, user_id)
            auth.login_user(session.get_session(), user_id)
            raise web.seeother('/after-signup')
        else:
            message = _('Please enter an username, full name, email, pasword, and language.')
            return template.tpl('register/reg', form, message)



class PageResendActivation:
    def GET(self):
        sess = session.get_session()
        auth.force_login(sess)

        user = database.dbget('users', sess.user_id)
        if not user:
            raise web.seeother('/')

        if user.activation == 0:
            raise web.seeother('/')

        hashed = hash(str(user.activation))
        send_activation_email(user.email, hashed, user.id)
        return template.lmsg('An email has been resent. <a href="/"><b>Back</b></a> |  <a href=""><b>Send another one</b></a>')


class PageAfterSignup:
    def phase1(self):
        '''
        Select at least 3 categories from the list
        '''
        db = database.get_db()
        categories_results = db.where(table='categories', order='name')
        categories = []
        for category in categories_results:
            cool_items_resutls = db.select(tables=['pins', 'pins_categories', 'categories', 'cool_pins'], what="pins.*",
                         where='pins.id=pins_categories.pin_id and pins_categories.category_id=categories.id'
                            ' and categories.id=$category_id'
                            ' and pins.id=cool_pins.pin_id'
                            ' and categories.id not in (select parent from categories where parent is not null)',
                         vars={'category_id': category.id})
            cool_items_list = list(cool_items_resutls)
            random_cool_items = []
            if len(cool_items_list) > 0:
                for _ in range(6):
                    if len(cool_items_list) == 0:
                        break
                    cool_item = random.choice(cool_items_list)
                    cool_items_list.remove(cool_item)
                    image_name = os.path.join('static', 'tmp', str(cool_item.id)) + '_cool.png'
                    if not os.path.exists(image_name):
                        continue
                    random_cool_items.append(cool_item)
                if len(random_cool_items) > 0:
                    category.cool_items = random_cool_items
                    categories.append(category)
        sess = session.get_session()
        results = db.where(table='users', what='username', id=sess.user_id)
        for row in results:
            username = row.username
            break
        else:
            username = ''
        return template.atpl('register/aphase1', categories, username, phase=1)

    _form1 = web.form.Form(web.form.Hidden('ids'))

    def phase2(self):
        '''
        Select at least 5 pins from the list
        '''
        sess = session.get_session()
        db = database.get_db()
        cool_pins = db.select(tables=['pins', 'cool_pins', 'user_prefered_categories'], what='pins.*',
                              where='pins.id=cool_pins.pin_id and cool_pins.category_id=user_prefered_categories.category_id'
                              ' and user_prefered_categories.user_id=$user_id',
                              order='timestamp desc',
                              vars={'user_id': sess.user_id})
        json_pins = []
        for cp in cool_pins:
            image_name = os.path.join('static', 'tmp', str(cp.id)) + '.png'
            image_name_thumb = os.path.join('static', 'tmp', 'pinthumb{}'.format(cp.id)) + '.png'
            if os.path.exists(image_name_thumb):
                cp.image_name = '/' + image_name_thumb
            elif os.path.exists(image_name):
                cp.image_name = '/' + image_name
            else:
                continue
            if not cp.name:
                cp.name = cp.description
            json_pins.append(json.dumps(cp))
        random.shuffle(json_pins)
        results = db.where(table='users', what='username', id=sess.user_id)
        for row in results:
            username = row.username
            break
        else:
            username = ''
        return template.atpl('register/aphase2', json_pins, username, phase=2)

    def phase3(self):
        '''
        Go to the profile
        '''
        sess = session.get_session()
        db = database.get_db()
        results = db.where(table='users', what='username', id=sess.user_id)
        username = results[0]['username']
        raise web.seeother(url="/{}".format(username), absolute=True)

    def GET(self, phase=None):
        '''
        Manages 3 phases of registration:

        1. Select categories
        2. select pins
        3. go to the profile
        '''
        auth.force_login(session.get_session())
        phase = int(phase or 1)
        try:
            return getattr(self, 'phase%d' % phase)()
        except AttributeError as e:
            raise web.notfound()


class ApiRegisterCategoryForUser:
    '''
    Adds and deletes prefered categories for the user

    For user via ajax.
    '''
    def PUT(self, category_id):
        '''
        Put a category in the prefered categories for this user
        '''
        sess = session.get_session()
        auth.force_login(sess)
        db = database.get_db()
        db.insert(tablename='user_prefered_categories', user_id=sess.user_id, category_id=category_id)
        web.header('Content-Type', 'application/json')
        return json.dumps({'status': 'ok'})

    def DELETE(self, category_id):
        '''
        Deletes a category from the prefered categories for this user
        '''
        sess = session.get_session()
        auth.force_login(sess)
        db = database.get_db()
        db.delete(table='user_prefered_categories', where='user_id=$user_id and category_id=$category_id',
                  vars={'user_id': sess.user_id, 'category_id': category_id})
        web.header('Content-Type', 'application/json')
        return json.dumps({'status': 'ok'})


class ApiRegisterCoolPinForUser(object):
    '''
    Adds and deletes cool items for the user

    For user via ajax.
    '''
    def PUT(self, pin_id):
        '''
        Put a cool item for this user
        '''
        sess = session.get_session()
        auth.force_login(sess)
        db = database.get_db()
        test_pin_exists = db.where(table='pins', repin=pin_id, user_id=sess.user_id)
        for _ in test_pin_exists:
            web.header('Content-Type', 'application/json')
            return json.dumps({'status': 'ok'})
        old_pin = db.where(table='pins', id=pin_id)[0]
        new_id = db.insert(tablename='pins', name=old_pin.name, description=old_pin.description,
                           user_id=sess.user_id, repin=pin_id, link=old_pin.link, category=old_pin.category,
                           views=0, tsv=old_pin.tsv)
        db.insert(tablename='likes', pin_id=new_id, user_id=sess.user_id)
        web.header('Content-Type', 'application/json')
        return json.dumps({'status': 'ok'})

    def DELETE(self, pin_id):
        '''
        Deletes a cool item from this user
        '''
        sess = session.get_session()
        auth.force_login(sess)
        db = database.get_db()
        new_pin = db.where(table='pins', repin=pin_id)[0]
        db.delete(table='likes', where='user_id=$user_id and pin_id=$pin_id',
                  vars={'user_id': sess.user_id, 'pin_id': new_pin.id})
        db.delete(table='pins', where='user_id=$user_id and id=$pin_id',
                  vars={'user_id': sess.user_id, 'pin_id': new_pin.id})
        web.header('Content-Type', 'application/json')
        return json.dumps({'status': 'ok'})



def send_activation_email(email, hashed, user_id):
    web.sendmail('noreply@mypinnings.com', email, 'Please activate your MyPinnings account',
                 str(template.tpl('email', hashed, user_id)), headers={'Content-Type': 'text/html;charset=utf-8'})

app = web.application(urls, locals())
