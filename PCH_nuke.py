import os
import PCH_ftrack
import PCH_io
import nuke
import platform

#######################################################################################

def move_node_pos(node, x, y,):
    xpos = node.xpos()
    ypos = node.ypos()
    node.setXYpos(xpos + x, ypos + y)

#######################################################################################

def get_read_from_VFX(vfx):
    user = os.environ['FTRACK_API_USER']
    api_key = os.environ['FTRACK_API_KEY']
    server = os.environ['FTRACK_SERVER']
    task_id = os.environ['FTRACK_TASKID']

    if platform.system() == 'Windows':
        OS = 'WIN'
        xsan = 'X:\\'
        spycerbox = 'W:\\'
    if platform.system() == 'Darwin':
        OS = 'MAC'
        xsan = '/Volumes/Xsan'
        spycerbox = '/Volumes/Xsan'

    session = PCH_ftrack.create_ftrack_session(api_user=user, api_key=api_key, server_url=server)
    task = session.query('Task where id is "{}"'.format(task_id)).one()
    #task = session.query('Task where name is "{}"'.format('py_test')).one()
    shot = task['parent']
    shot_name = shot['name']
    print str(shot_name)
    episode = shot['parent']
    project_path = None

    if episode['name'].startswith('Ep'):
        print 'startswith episode'
        episode_name = episode['name']
        project = episode['parent']
        project_name = project['name']

    else:
        print 'startswith something else'
        episode_name = None
        project = shot['parent']
        project_name = project['name']


    if project_name.split('_')[0].lower() == 'ad':
        project_path = os.path.normpath(spycerbox + 'Projects\\')
    if project_name.split('_')[0].lower() == 'tv':
        project_path = os.path.normpath(xsan + 'Projects\\')

    folders = os.listdir(project_path)
    project = filter(lambda x: x.lower() == project_name, folders)


    if episode_name != None:
        toVFX_path = os.path.join(project_path, project[0], 'VFX', 'toVFX', episode_name, shot_name)
        fromVFX_path = os.path.join(project_path, project[0], 'VFX', 'fromVFX', episode_name, shot_name)
        print 'task: {}\nshot: {}\nepisode: {}\nproject: {}'.format(task['name'],shot_name,episode_name,project_name)
        print toVFX_path
    else:
        toVFX_path = os.path.join(project_path, project[0], 'VFX', 'toVFX', shot_name)
        fromVFX_path = os.path.join(project_path, project[0], 'VFX', 'fromVFX', shot_name)
        print 'task: {}\nshot: {}\n\nproject: {}'.format(task['name'], shot_name, project_name)
        print toVFX_path

    if vfx == 'toVFX':
        sequences = PCH_io.FileSequences(toVFX_path)
    if vfx == 'fromVFX':
        sequences = PCH_io.FileSequences(fromVFX_path)

    for read in sequences:
        read_node = nuke.createNode('Read')
        read_node['file'].setValue(read['nuke_read'])
        read_node['origfirst'].setValue(read['frame_range'][0])
        read_node['origlast'].setValue(read['frame_range'][1])
        read_node['first'].setValue(read['frame_range'][0])
        read_node['last'].setValue(read['frame_range'][1])
        if len(sequences) > 1:
            if read['nuke_read'].find('MAIN') != -1:
                set_frame_range_from_read(node=read_node)
        else:
            set_frame_range_from_read(node=read_node)

#######################################################################################

def create_pch_writes():

    def read_node(selected_node):

        to_from_vfx = selected_node['file'].value().replace('toVFX', 'fromVFX')
        path, filename = os.path.split(to_from_vfx)
        output = filename.replace('_BG', '_MAIN')
        splitted_matte_path = path.split('/')
        splitted_matte_path.append('matte')
        matte_path = '/'.join(splitted_matte_path) + '/' + output


        return {'read_file': selected_node['file'].value(),
                'file_output': os.path.join(path, output).replace('\\', '/'),
                'matte_output': matte_path,
                'read_colorspace': selected_node['colorspace'].value(),
                'first_frame': selected_node['origfirst'].value(),
                'last_frame': selected_node['origlast'].value()
                }

    def create_write_node(node, write_type, colorspace_override=None):

        output_keys = {'fromVFX': node['file_output'], 'matte': node['matte_output']}
        output_file = output_keys[write_type]

        if colorspace_override == None:
            colorspace_selection = {'fromVFX': node['read_colorspace'], 'matte': 'ACES - ACEScg'}
            colorspace = colorspace_selection[write_type]
        else:
            colorspace = colorspace_override

        write_node = nuke.Node('Write')
        write_node['file'].setValue(output_file)
        write_node["create_directories"].setValue(1)
        write_node["colorspace"].setValue(colorspace)
        write_node["postage_stamp"].setValue(1)
        write_node["use_limit"].setValue(1)
        write_node["first"].setValue(node['first_frame'])
        write_node["last"].setValue(node['last_frame'])
        return write_node

    # Jos write nodea ei valittu, annetaan virhe
    valittu=nuke.selectedNode()
    rn = read_node(valittu)
    dot_a = nuke.createNode('Dot')
    dot_b = nuke.createNode('Dot')
    move_node_pos(dot_a, 0, 50)
    move_node_pos(dot_b, 0, 200)
    wn_a = create_write_node(node=rn, write_type='fromVFX')
    move_node_pos(wn_a, 0, 50)
    nuke.toNode(dot_b['name'].value())
    wn_b = create_write_node(node=rn, write_type='matte')
    wn_b.connectInput(0, dot_b)
    move_node_pos(wn_b, 150, 50)

#######################################################################################

def set_frame_range_from_read(node=None):
    if node is None:
        node = nuke.selectedNode()
    first = node['first'].value()
    last = node['last'].value()
    nuke.toNode('root')['first_frame'].setValue(first)
    nuke.toNode('root')['last_frame'].setValue(last)

#######################################################################################



