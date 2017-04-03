import os
import platform
import logging
import re
from logging.handlers import TimedRotatingFileHandler

#######################################################################################

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(
            'debug.log',
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

def log_dict(dict):
    ident = '\t' * 2
    s = 'Dictionary key : values'
    for k, v in dict.iteritems():
        s = s + '\n{}{}: {}'.format(ident, k, v)
    logger.debug(s)

#######################################################################################

def FileSequences(path, prefix=None):
    # If path does not found
    if not os.path.isdir(path):
        logger.error('Path not found!\n'
                     '{0}path: {1}, prefix: {2}'.format(ident, path, prefix))
        return 0

    def validate_filesequence(f):
        # check if extension is supported
        if not os.path.splitext(f)[-1] in supported_formats:
            return 0
        # Assume that if file is splitted with '.' and splitted file length is 3 its file sequence
        split_file = f.split('.')
        if not len(split_file) == 3:
            # Check if digits are seperated with '.' or '_'
            if not re.split('[\.,_]', f)[-2].isdigit():
                # Check if digits are not seperated from end
                digit_list = [s for s in split_file[0] if s.isdigit()]
                digit_list = re.findall(r'\d+', split_file[-2])
                digits = int(''.join([s for s in split_file[0] if s.isdigit()]))
                if type(digits) != int:
                    logger.warning('Couldnt parse with digits: {}'.format(f.split('.')))
                    return -1
        return 1

    def get_base_from_file(f):
        split_file = f.split('.')
        if len(split_file) == 3:
            return split_file[0]
        if len(split_file) == 2:
            split_file = f.split('.')[0].split('_')
            del split_file[-1]
            return '_'.join(split_file)

    def digits_min(a, b):
        ''' Returns minimum number '''
        return b if b < a else a

    def digits_max(a, b):
        ''' Returns maximum number '''
        return b if b > a else a

    def get_frame_range(files):
        min_digits = 99999999999999999
        max_digits = -1
        for f in files:
            file_splitted = re.split('[\.,_]', f)
            if not file_splitted[-2].isdigit():
                digits = ''.join([s for s in file_splitted[-2] if s.isdigit()])
                if digits == '':
                    return -1
                min_digits = digits_min(min_digits, int(digits))
                max_digits = digits_max(max_digits, int(digits))
            else:
                min_digits = digits_min(min_digits, int(file_splitted[-2]))
                max_digits = digits_max(max_digits, int(file_splitted[-2]))
        frame_range = (min_digits, max_digits)
        # return validate_frame_range(files, frame_range)
        return frame_range

    def get_subtype(file):
        test = file.lower()
        if test.find('_ep') != -1:
            return 'episode'
        elif test.find('_fx') != -1:
            return 'fx'
        else:
            return 'other'

    def format_ffmpeg_padding(padding):
        ''' Create digit padding compatible with FFMPEG'''
        return '%{}d'.format(str(padding).zfill(2))

    def create_sequence(files, path):
        def find_missing_frames(files, frame_range):
            set_of_frames = set(range(frame_range[0], frame_range[1]+1))
            for f in files:
                file_splitted = re.split('[\.,_]', f)
                digits = int(''.join([s for s in file_splitted[-2] if s.isdigit()]))
                set_of_frames.remove(digits)
            return set_of_frames
        splitted_file = re.split('[\.,_]', files[0])
        base = "_".join(splitted_file[:-2])
        frame_range = get_frame_range(files)
        if frame_range == -1:
            return -1
        duration = frame_range[1]-frame_range[0]+1
        padding = len(splitted_file[-2])
        middle_frame = str(frame_range[0]+(int(duration/2))).zfill(len(splitted_file[-2]))
        nuke_read = ".".join((base,'#'*padding,splitted_file[-1]))
        sequence = {
            'type': 'FileSequence',
            'files': files,
            'subtype': get_subtype(files[0]),
            'path': path,
            'ext': splitted_file[-1],
            'frame_range': frame_range,
            'padding': len(splitted_file[-2]),
            'duration': duration,
            'to_thumbnail': ".".join((base,middle_frame,splitted_file[-1])),
            'to_movie': base+'.'+format_ffmpeg_padding(padding)+'.'+splitted_file[-1],
            'nuke_read': os.path.join(path, nuke_read).replace('\\', '/')
        }

        if sequence['subtype'] == 'episode':
            sequence['episode'] = splitted_file[1]
            sequence['fx_shot'] = splitted_file[2][:2] + '_' + splitted_file[2][2:]
            sequence['layer'] = splitted_file[3]

        if sequence['subtype'] == 'fx':
            sequence['episode'] = None
            sequence['fx_shot'] = splitted_file[1][:2] + '_' + splitted_file[1][2:]
            sequence['layer'] = splitted_file[2]

        if sequence['subtype'] == 'other':
            sequence['episode'] = None
            sequence['fx_shot'] = None
            sequence['layer'] = None

        if sequence['duration'] != len(files):
            missing_frames = find_missing_frames(files, sequence['frame_range'])
            logger.warning(
                'Frame range not valid! first: {}, last: {}, duration: {},'
                'len(files): {}\n{}Missing frames: {}'
                .format(sequence['frame_range'][0], sequence['frame_range'][1],
                sequence['duration'], len(files), ident, missing_frames)
            )
            return -1
        return sequence

    sequences = []
    supported_formats = ['.dpx', '.exr', '.jpg', '.png']
    root = os.listdir(path)
    # Filter all files which extension aint in supported formats
    # Filter all files if not finding digits before extension
    filttered_files = filter(validate_filesequence, root)
    if len(filttered_files) < 2:
        return -1
    num_sequences = set(sorted(map(get_base_from_file, filttered_files)))
    logger.debug(num_sequences)
    if prefix != None:
        logger.debug('going prefix')
        for seq in num_sequences:
            files = filter(lambda x: x.find(prefix) != -1, filttered_files)
            if not files:
                logger.warning('Couldn\'t find FileSequence with prefix: '.format(prefix))
                continue
        if not files:
            return -1
        sequence = create_sequence(files, path)
        if sequence == -1:
            return -1
        log_dict(sequence)
        sequences.append(sequence)
    else:
        logger.info('going sequences')
        for seq in num_sequences:
            logger.info('seq: {} '.format(seq))
            files = filter(lambda x: x.find(seq) != -1, filttered_files)
            sequence = create_sequence(files, path)
            if sequence == -1:
                return -1
            log_dict(sequence)
            sequences.append(sequence)

    return sequences

#######################################################################################

def create_thumbnail(fileseq, colorspace='log', update=False):
    from wand.image import Image
    '''
    Create thumbnail to ./ftrack folder
    :param fileseq: File sequence dictionary with additional information from
                    get_sequence_information() function
    :returns: full path where thumbnail was created
    '''
    path, filename = fileseq['path'], fileseq['to_thumbnail']
    os.chdir(path)
    ftrack_path = os.path.join(path, 'ftrack')
    filename_split = filename.split('.')
    digits = filename_split[1]
    filename_split = filename_split[0].split('_')

    filename_split[-1] = 'THUMB'
    thumb = "_".join(filename_split)
    thumb = thumb + '.' + digits + '.jpg'
    export_to = os.path.join(ftrack_path, thumb)
    fileseq['thumbnail_location'] = export_to

    if not os.path.exists(ftrack_path):
        logger.info('ftrack folder not exists lets try to create it')
        os.mkdir(ftrack_path)

    if os.path.isfile(export_to):
        if update == False:
            logger.info("File already exists. Let's skip the file!")
            return export_to
        else:
            logger.info('File already exists. Updating file!')

    with Image(filename=filename) as original:
        with original.convert('jpg') as converted:
            w = original.width
            h = original.height

            thumb_width = 1920
            aspect = float(thumb_width) / float(w)
            thumb_height = int(h * aspect)

            converted.colorspace = colorspace
            converted.resize(thumb_width, thumb_height)

            converted.save(filename=export_to)
            logger.info('File saved: {}'.format(export_to))

            return export_to

#######################################################################################

def create_movie_from_file_sequence(fileseq, lut='AlexaLogC', fps='25', codec='H264', update=False):
    import ffmpy
    '''
    Creates movie file to ./ftrack/ folder.
    :param fileseq: file_sequence dictionary with additional information
    :param fps: framerate
    :param update: will it update file or not
    :returns: full path where movie was created
    '''
    path, filename = fileseq['path'], fileseq['to_movie']
    os.chdir(path)
    ftrack_path = os.path.join(path, 'ftrack')
    filename_split = filename.split('.')[0].split('_')
    filename_split[-1] = codec
    movie_file = "_".join(filename_split) + '.mp4'
    export_to = os.path.join(ftrack_path, movie_file)
    start_frame, end_frame = fileseq['frame_range'][0], fileseq['frame_range'][1]
    fileseq['fps'] = fps
    fileseq['movie_location'] = export_to

    if not os.path.exists(ftrack_path):
        logger.info('ftrack folder not exists lets try to create it')
        os.mkdir(ftrack_path)

    if os.path.isfile(export_to):
        if update == False:
            logger.info( "File already exists. Let's skip the file!")
            return export_to
        else:
            logger.info('File already exists. Updating file!')
            os.remove(export_to)

    if platform.system() == 'Windows':
        prefix = '\'X\:'
    if platform.system() == 'Darwin':
        prefix = '/Volumes/Xsan'

    lut_path = '/3D_server/luts/'

    supported_luts = {
        'AlexaLogC': 'AlexaV3_EI0800_LogC2Video_Rec709_LL_nuke3d.cube'
    }


    if lut in supported_luts:
        lut_var = prefix + lut_path + supported_luts[lut]
        ff = ffmpy.FFmpeg(
            inputs={filename: '-start_number {} -framerate {}'.format(start_frame, fps)},
            outputs={export_to: '-ac 2 -b:v 2000k -c:a aac -c:v libx264 -pix_fmt yuv420p -g 30 -vf lut3d="{}" -vf scale="trunc((a*oh)/2)*2:720" -b:a 160k -vprofile high -bf 0 -strict experimental -f mp4'.format(lut_var)}
        )
    else:
        ff = ffmpy.FFmpeg(
            inputs={filename: '-start_number {} -framerate {}'.format(start_frame, fps)},
            outputs={
                export_to: '-ac 2 -b:v 2000k -c:a aac -c:v libx264 -pix_fmt yuv420p -g 30 -vf scale="trunc((a*oh)/2)*2:720" -b:a 160k -vprofile high -bf 0 -strict experimental -f mp4'}
        )

    logger.debug(ff.cmd)
    ff.run()

    duration = fileseq['frame_range'][0] - fileseq['frame_range'][1]

    logger.debug('file: {}\nstart_frame: {}, end_frame: {}, fps: {}, duration: {}'.format(export_to, start_frame, end_frame, fps, duration))
    return export_to

#######################################################################################

def collect_folder(folder, prefix=None):
    ''' Collect folders with prefix search '''
    if prefix == None:
        logger.info('Give me prefix')
        return []
    root = os.listdir(folder)
    folders = sorted(filter(lambda x: x.startswith(prefix), root))
    return folders

#######################################################################################

def collect_episode_fx_recursive(path):
    '''
    Collects fx shots from episodes recursively
    :param path: path where to start
    :returns: all fx shots with full path
    '''

    episodes = collect_folder(path, prefix='Ep')
    fullpath_episodes = map(lambda x: os.path.join(path, x), episodes)
    all_fxshots = []
    for ep in fullpath_episodes:
        fx_shots = collect_folder(ep, prefix='FX_')
        fullpath_fx_shots = map(lambda x: os.path.join(ep, x), fx_shots)
        all_fxshots.extend(fullpath_fx_shots)
    return all_fxshots

#######################################################################################

def collect_fx_recursive(path):
    '''
    Collects fx shots from episodes recursively
    :param path: path where to start
    :returns: all fx shots with full path
    '''

    fx_folder = collect_folder(path, prefix='FX_')
    fullpath_fx = map(lambda x: os.path.join(path, x), fx_folder)
    return fullpath_fx

#######################################################################################

#######################################################################################