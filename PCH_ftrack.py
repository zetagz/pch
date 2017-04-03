import logging
from logging.handlers import TimedRotatingFileHandler

#######################################################################################

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(
            'debug_ftrack.log',
            when='m',
            interval=1,
            backupCount=10)

ident = '\t'*2

formatter = logging.Formatter(
    '%(levelname)s:\t%(asctime)s\t[ %(name)s::{1}::%(funcName)s ]\n{0}%(message)s\n'.format(
        ident, __name__))

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

#######################################################################################

def create_ftrack_session(api_user, api_key, server_url):
    ''' Creates ftrack session '''
    import ftrack_api
    session = ftrack_api.Session(
        server_url=server_url,
        api_key=api_key,
        api_user=api_user
    )
    return session

#######################################################################################

def get_ftrack_project(session, project_name):
    return session.query('Project where name like "{}"'.format(project_name)).first()

#######################################################################################

def get_task_by_id(session, task_id):
    return session.query('Task where id is "{}"'.format(task_id)).one()

#######################################################################################

def get_ftrack_project_shots(session, project):
    return session.query('Shot where project.id is "{}"'.format(project['id'])).all()

#######################################################################################

def get_ftrack_episode_shots(session, episode):
    return session.query('Shot where parent.id is "{}"'.format(episode['id'])).all()

#######################################################################################

def get_ftrack_episode(session, episode_name, parent_id):
    return session.query('Episode where project.id is "{}" and'
                         '(name is "{}")'
                         .format(parent_id, episode_name)).first()

#######################################################################################

def get_ftrack_shot(session, fxshot_name, parent_id):
    return session.query('Shot where parent.id is "{}" and'
                         '(name is "{}")'
                         .format(parent_id, fxshot_name)).first()

#######################################################################################

def get_ftrack_shot_tasks(session, shot_id):
    return session.query('Task where parent.id is "{}"'.format(shot_id)).all()

#######################################################################################

def get_ftrack_asset_version(session, asset):
    return session.query('AssetVersion where asset.id is "{}"'.format(asset['id'])).all()

#######################################################################################

def get_ftrack_assets(session, shot):
    return session.query('Asset where parent.id is "{}"'.format(shot['id'])).all()

#######################################################################################

def create_asset_version(session, task, asset):
    status = session.query('Status where name is "Not Started"').one()
    version = session.create('AssetVersion', {
        'asset': asset,
        'status': status,
        'comment': 'Dailies',
        'task': task
    })
    return version

#######################################################################################

def create_asset(session, shot, asset_name='dailies'):
    asset_type = session.query('AssetType where short is "upload"').first()
    asset = session.create('Asset', {
        'parent': shot,
        'name': asset_name,
        'type': asset_type
    })
    return asset

#######################################################################################

def create_webview_component(session, version, fileseq):
    server_location = session.query('Location where name is "ftrack.server"').one()
    component = version.create_component(
        path=fileseq['movie_location'],
        data={
            'name': 'ftrackreview-mp4'
        },
        location=server_location
    )
    component['metadata']['ftr_meta'] = json.dumps({
        'frameIn': fileseq['frame_range'][0],
        'frameOut': fileseq['frame_range'][1],
        'frameRate': fileseq['fps']
    })
    version.create_thumbnail(fileseq['thumbnail_location'])
    component.session.commit()
    logger.info('Component created in fx: {}'.format(fileseq['fx_shot']))
    return 1

#######################################################################################