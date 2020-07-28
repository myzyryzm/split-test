#!/usr/bin/env python
import os,sys
thispath = os.path.dirname(os.path.abspath(__file__))
import json
import subprocess
import argparse
import shutil
sys.path.append(os.path.join(thispath,'..'))
from utils import fstr, file_exist_check, make_directory, get_file_name, append_slash, append_postfix

jetson_check_file = '/evt/automation-scripts-misc/jetson/initial_setup/setup_utils_tx_version.sh'
is_jetson = False
if os.path.isfile(jetson_check_file):
    is_jetson = bool(0 == subprocess.call(['bash', jetson_check_file]))


# the following pipeline is only compatible with ubuntu 18.04 (jetpack 4);      note the last two args are "width,height"
#GST_LAUNCH_CMD = '''gst-launch-1.0 uridecodebin name='src' uri=file://{} ! nvvideoconvert src-crop={}:{}:{}:{} ! 'video/x-raw,format=(string)I420' ! omxh264enc ! 'video/x-h264,stream-format=(string)byte-stream' ! h264parse ! qtmux name="mux" ! filesink name='sink' location={} src. ! audioconvert ! 'audio/x-raw, format=(string)S16LE, layout=(string)interleaved, rate=(int)44100, channels=(int)2' ! voaacenc ! aacparse ! mux.'''
# the following pipeline is backwards compatible with ubuntu 16.04 (jetpack 3); note the last args are "right,bottom" and then "width,height"
GST_LAUNCH_CMD = '''gst-launch-1.0 uridecodebin name='src' uri=file://{} ! nvvidconv left={} top={} right={} bottom={} ! 'video/x-raw,format=(string)I420,width={},height={},pixel-aspect-ratio=1/1' ! omxh264enc ! 'video/x-h264,stream-format=(string)byte-stream' ! h264parse ! qtmux name="mux" ! filesink name='sink' location={} src. ! audioconvert ! 'audio/x-raw, format=(string)S16LE, layout=(string)interleaved, rate=(int)44100, channels=(int)2' ! voaacenc ! aacparse ! mux.'''


def ffmpeg_split(video: str, start: float, duration: float, output: str, audio:bool, is_final_end_of_video:bool, docrop:dict={}):
    """
    Uses a subprocess call to use FFMPEG to split a video
    """
    if is_final_end_of_video:
        toend = ["-t", fstr(duration)]
    else:
        toend = ["-t", fstr(duration)]
    split_video = ["ffmpeg", "-nostdin", "-y", "-ss", fstr(start)] + toend + ["-i", video, "-vcodec"]
    if is_jetson:
        split_video += ["copy",]
    else:
        split_video += ["h264_nvenc",]
        if docrop:
            split_video += ['-vf', 'crop=%d:%d:%d:%d' % (docrop['width'],docrop['height'],docrop['col0'],docrop['row0'])]
    if audio:
        split_video += ["-acodec", "aac", "-strict", "-2", output]
    else:
        assert 0, str(audio)+"\nHIGHLY suggest including audio in slide videos; it is now considered a bug to have slide videos without audio"
        split_video += ["-an", output]
    print(' '.join(split_video))
    subprocess.run(split_video, stderr=subprocess.DEVNULL)

    if is_jetson and False: # WARNING: THE GSTREAMER PIPELINE FOR CROPPING IS BROKEN ON THE JETSON RIGHT NOW, SINCE GSTREAMER OCCASIONALLY FREEZES FOR SOME VIDEOS
        output_temp = output + '.temp.mpg'
        cmd = GST_LAUNCH_CMD.format(output, docrop['col0'], docrop['row0'], docrop['col0']+docrop['width'], docrop['row0']+docrop['height'], docrop['width'], docrop['height'], output_temp)
        subprocess.run(cmd, shell=True)
        shutil.move(output_temp, output)


def split_hdmi(hdmi_path: str, json_timing: dict, output_dir: str, post_fix:str="", audio:bool=True, crop_coords_per_slide:list=[]):
    """
    Takes an hdmi video as input and splits it into multiple videos.
    The post_fix string is used to append to the end of the output files.
    Audio defaults to true: April 2019 decision to always include audio in slides (to be muted by frontend, sometimes, depending on layout).
    """
    # Generate the output directory if it does not exist.
    make_directory(output_dir)

    OFFSETDELAY = 0.4

    # check arg
    if len(crop_coords_per_slide) > 0:
        assert len(crop_coords_per_slide) == len(json_timing['allId']), str(len(crop_coords_per_slide))+' vs '+str(len(json_timing['allId']))

    # Start splitting the videos based off the timings.
    # NOTE: The videos will be in the order dictated by allId!!!!
    finalidx = int(len(json_timing['allId'])) - 1
    for index, slide_id in enumerate(json_timing['allId']):
        # Get timing attributes
        time_start = float(json_timing['byId'][slide_id]['start']) + OFFSETDELAY
        time_end   = float(json_timing['byId'][slide_id]['end']) + OFFSETDELAY
        duration = time_end - time_start

        # Generate the output file name
        output_file = append_slash(output_dir) + append_postfix(get_file_name(hdmi_path), post_fix + str(index))

        # Start splitting
        print('Splitting HDMI video to file %s'% output_file)
        docrop = None
        if len(crop_coords_per_slide) > 0:
            docrop = crop_coords_per_slide[index]
            assert isinstance(docrop,dict), str(index)+': '+str(type(docrop))
        ffmpeg_split(hdmi_path, time_start, duration, output_file, audio, is_final_end_of_video=(index>=finalidx), docrop=docrop)


def parse_args(sys_argv):
    #assert len(sys.argv) >= 2, 'Usage: ./%s %s' % (os.path.basename(__file__), '<HDMI_VIDEO> <JSON_TIMING> <OUTPUT_DIRECTORY> <POST_FIX> [KEEP_AUDIO]')
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--video', type=str, help='hdmi video', required=True)
    parser.add_argument('-j', '--json',  type=str, help='timing json')
    parser.add_argument('-o', '--outdir',type=str, help='output directory to save videos')
    parser.add_argument('-p', '--postfix',type=str,help='suffix to append to filenames')
    parser.add_argument('-a', '--audio', action='store_true', help='save audio in split videos')
    return parser.parse_args(sys_argv)


def preprep_for_hdmi_split(args):

    # Grab all necessary inputs
    hdmi_path = file_exist_check(args.video)

    if args.json is not None and len(args.json) > 1:
        json_path = file_exist_check(args.json)
    else:
        json_path = file_exist_check(args.video[:args.video.rfind('.')]+'_timings.json')

    if args.outdir is not None and len(args.outdir) > 1:
        output_dir = os.path.abspath(args.outdir)
    else:
        baseh = os.path.basename(hdmi_path)
        output_dir = os.path.join(os.path.dirname(hdmi_path), baseh[:baseh.rfind('.')]+'_output')

    # String pattern to append to the end of the generated files
    if args.postfix is None:
        args.postfix = ""

    # Open the json timing and pass it to the splitter
    with open(json_path, 'r') as json_file:
        json_object = json.load(json_file)

    return hdmi_path, json_object, output_dir, args.postfix, args.audio

args = parse_args(sys.argv[1:])
split_hdmi(*preprep_for_hdmi_split(args))
