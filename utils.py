from settings import settings


def get_short_link(name):
    full_url = '%s/%s' % (settings['redirect_domain'], name)
    short_url = full_url.replace('https://', '').replace('http://', '')
    return '<%s|%s>' % (full_url, short_url)
