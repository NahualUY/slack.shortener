# coding=utf-8
from flask import Flask, request, redirect
from settings import settings
import models
import requests
import json
import validators
import re
import logging
app = Flask(__name__)

if 'log_path' in settings and settings['log_path']:
    handler = logging.handlers.RotatingFileHandler(settings['log_path'])
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(handler)


@app.route("/commands", methods=['POST'])
def execute_command():
    if request.form['token'] not in settings['slack']['command_tokens']:
        return 'Error'

    text = re.sub(' +', ' ', request.form['text'].strip())
    parts = text.split(' ')
    if parts[0] == 'help':
        return (u'`/url`\n>Muestra todas las urls creadas\n\n'
                u'`/url [url-corta] [url-real]`\n'
                u'>Crea un link desde {base_url}/url-corta a url_real y *avisa en el canal que el link fué creado*\n>\n'
                u'>*Ejemplo*: `/url facebook https://www.facebook.com/groups/NahualUY201508` Hace que <{base_url}/facebook> redirija a https://www.facebook.com/groups/NahualUY201508\n\n'
                u'`/url [url-corta]`\n'
                u'>Muestra a qué url apunta {base_url}/url-corta y quién lo creó\n>\n'
                u'>*Ejemplo*: `/url facebook` muestra\n>_{base_url}/facebook apunta a https://www.facebook.com/groups/NahualUY201508 (creado por @gmc)_\n\n'
                u'`/url @[alguien]`\n'
                u'>Muestra todas las urls creadas por @alguien\n\n'
                u'`/url.del [url-corta]`\n'
                u'>Borra la url {base_url}/url-corta\n>\n'
                u'>*Importante:* Sólo quien creó la url la puede borrar o un administrador de Slack').format(
            base_url=settings['redirect_domain'])

    if request.form['command'] == '/url':
        previous_url = None
        try:
            previous_url = models.Url.get(models.Url.name == parts[0])
        except models.Url.DoesNotExist:
            pass

        if len(parts) == 1 and not parts[0]:
            urls = sorted(list(models.Url.select()), key=lambda u: u.created_by_id)
            if len(urls):
                return '*Urls creadas*\n%s' % '\n'.join(['<%s/%s> -> <%s> (creada por <@%s>)' % (settings['redirect_domain'], u.name, u.dest_url, u.created_by_id) for u in urls])
            else:
                return 'No hay urls'

        if len(parts) == 1:
            if parts[0][0] == '@':
                # get the user id for this username
                data = {'token': settings['slack']['web_api_token'], 'user': request.form['user_id']}
                r = requests.get('https://slack.com/api/users.list', data)
                response = json.loads(r.content)

                user_id = next((u['id'] for u in response['members'] if u['name'] == parts[0][1:]), None)
                if not user_id:
                    return 'No hay un usuario %s' % parts[0]

                urls = list(models.Url.select().where(models.Url.created_by_id == user_id))
                if len(urls):
                    return '*Urls creadas por <@%s>:*\n%s' % (user_id, '\n'.join(['<%s/%s> -> <%s>' % (settings['redirect_domain'], u.name, u.dest_url) for u in urls]))
                else:
                    return 'No hay urls creadas por <@%s>' % user_id

            elif previous_url:
                return '<%s/%s> apunta a <%s> (creado por <@%s>)' % (settings['redirect_domain'], previous_url.name, previous_url.dest_url, previous_url.created_by_id)
            else:
                return 'No hay un link definido para <%s/%s>' % (settings['redirect_domain'], parts[0])

        if len(parts) != 2:
            return '*Error*\nSe debe usar `/url [url-corta] [url-real]`.\nPara crear un link desde %s/web a http://nahual.uy se debe usar `/url web http://nahual.uy`' % settings['redirect_domain']

        if not validators.url(parts[1]):
            parts[1] = 'http://%s' % parts[1]
            if not validators.url(parts[1]):
                return u'*Error:* El segundo parámetro tiene que ser una URL'

        if previous_url:
            return u'*Error*\nYa existe un link <%s/%s> creado por <@%s>. Apunta a <%s>. Sólo <@%s> o un administrador lo puede borrar usando `/url.del`' % (settings['redirect_domain'], parts[0], previous_url.created_by_id, previous_url.dest_url, previous_url.created_by_id)

        new = models.Url(name=parts[0], dest_url=parts[1], created_by_id=request.form['user_id'], created_by_username=request.form['user_name'])
        new.save()

        data = {
            'text': u'<@%s> creó el link <%s/%s> que apunta a <%s>' % (new.created_by_id, settings['redirect_domain'], new.name, new.dest_url),
            'channel': '#%s' % request.form['channel_name'],
            'username': settings['slack']['incoming_webhook']['username'],
            'icon_url': settings['slack']['incoming_webhook']['icon_url']
        }
        requests.post(settings['slack']['incoming_webhook']['url'], json=data)
        return ''

    elif request.form['command'] == '/url.del':
        try:
            url = models.Url.get(models.Url.name == request.form['text'])
        except models.Url.DoesNotExist:
            return '*Error:* No existe el link %s' % request.form['text']

        ok = url.created_by_id == request.form['user_id']
        if not ok:
            # check if the user is admin
            data = {'token': settings['slack']['web_api_token'], 'user': request.form['user_id']}
            r = requests.get('https://slack.com/api/users.info', data)
            response = json.loads(r.content)
            ok = response['ok'] and response['user']['is_admin']

        if ok:
            url.delete_instance()
            return 'Link borrado!'
        else:
            return u'*Error:* Sólo <@%s> o un administrador puede borrar el link <%s/%s>' % (url.created_by_id, settings['redirect_domain'], url.name)


@app.route('/<path:path>')
def catch_all(path):
    try:
        url = models.Url.get(models.Url.name == path)
        return redirect(url.dest_url)
    except models.Url.DoesNotExist:
        return 'Page not found', 404


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=8081)
