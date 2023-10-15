# -*- coding:utf-8 -*-
# Author: Jiri Sindelar

# Thanks to Zhang Laichi for numerous code pieces
# https://github.com/laciechang/resolve_batch_io_point/tree/main

# Thanks to Igor Ridanovic for providing the timecode conversion method
# https://github.com/IgorRidanovic/smpte

fu = bmd.scriptapp('Fusion')
ui = fu.UIManager
disp = bmd.UIDispatcher(ui)


class SMPTE(object):
    '''Frames to SMPTE timecode converter and reverse.'''
    def __init__(self):
        self.fps = 24.0
        self.df  = False
        self.fps_mapping = {
            '16': 16.0,     '18': 18.0,
            '23': 23.976,   '24': 24.0,
            '24.0': 24.0,
            '25': 25.0,     '29': 29.97,
            '30': 30.0,     '30.0': 30.0,
            '47': 47.952,
            '48': 48.0,     '50': 50.0,
            '59': 59.94,    '60': 60.0,
            '72': 72.0,     '95': 95.904,
            '96': 96.0,     '100': 100.0,
            '119': 119.88,  '120': 120.0
            }

    def set_fps(self, str_fps):
        self.fps = self.fps_mapping[str_fps]

    def get_frames(self, tc):
        '''Converts SMPTE timecode to frame count.'''

        if not tc or tc == '':
            return None
        
        if int(tc[9:]) > self.fps:
            raise ValueError('SMPTE timecode to frame rate mismatch.', tc, self.fps)

        hours   = int(tc[:2])
        minutes = int(tc[3:5])
        seconds = int(tc[6:8])
        frames  = int(tc[9:])

        totalMinutes = int(60 * hours + minutes)
        
        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.df:
            dropFrames = int(round(self.fps * 0.066666))
            timeBase   = int(round(self.fps))
            hourFrames   = int(timeBase * 60 * 60)
            minuteFrames = int(timeBase * 60)
            frm = int(((hourFrames * hours) + (minuteFrames * minutes) + (timeBase * seconds) + frames) - (dropFrames * (totalMinutes - (totalMinutes // 10))))
        # Non drop frame calculation.
        else:
            self.fps = int(round(self.fps))
            frm = int((totalMinutes * 60 + seconds) * self.fps + frames)

        return frm

    def get_tc(self, frames):
        '''Converts frame count to SMPTE timecode.'''

        frames = abs(frames)

        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.df:

            spacer = ':'
            spacer2 = ';'

            dropFrames         = int(round(self.fps * .066666))
            framesPerHour      = int(round(self.fps * 3600))
            framesPer24Hours   = framesPerHour * 24
            framesPer10Minutes = int(round(self.fps * 600))
            framesPerMinute    = int(round(self.fps) * 60 - dropFrames)

            frames = frames % framesPer24Hours

            d = frames // framesPer10Minutes
            m = frames % framesPer10Minutes

            if m > dropFrames:
                frames = frames + (dropFrames * 9 * d) + dropFrames * ((m - dropFrames) // framesPerMinute)
            else:
                frames = frames + dropFrames * 9 * d

            frRound = int(round(self.fps))
            hr = int(frames // frRound // 60 // 60)
            mn = int((frames // frRound // 60) % 60)
            sc = int((frames // frRound) % 60)
            fr = int(frames % frRound)

        # Non drop frame calculation.
        else:
            self.fps = int(round(self.fps))
            spacer  = ':'
            spacer2 = spacer

            frHour = self.fps * 3600
            frMin  = self.fps * 60

            hr = int(frames // frHour)
            mn = int((frames - hr * frHour) // frMin)
            sc = int((frames - hr * frHour - mn * frMin) // self.fps)
            fr = int(round(frames -  hr * frHour - mn * frMin - sc * self.fps))

        # Return SMPTE timecode string.
        return(
                str(hr).zfill(2) + spacer +
                str(mn).zfill(2) + spacer +
                str(sc).zfill(2) + spacer2 +
                str(fr).zfill(2)
                )


def this_pj():
    resolve = bmd.scriptapp('Resolve')
    pj_manager = resolve.GetProjectManager()
    current_pj = pj_manager.GetCurrentProject()
    return current_pj


def this_timeline():
    return this_pj().GetCurrentTimeline()


def get_all_track_clips(track_num=2, track_type='video'):
    return this_timeline().GetItemsInTrack(track_type, track_num)


markercolor_names = [
    'Blue',
    'Cyan',
    'Green',
    'Yellow',
    'Red',
    'Pink',
    'Purple',
    'Fuchsia',
    'Rose',
    'Lavender',
    'Sky',
    'Mint',
    'Lemon',
    'Sand',
    'Cocoa',
    'Chocolate',
    'Cream'
]

window_01 = ui.VGroup([
        ui.VGroup({"Spacing": 5, "Weight": 1},[
            ui.HGroup({"Spacing": 5, "Weight": 0},[
                ui.CheckBox({"ID": 'split_by_color', "Text": "Split By Color:", "Checked": True, "AutoExclusive": True, "Checkable": True, "Events": {"Toggled": True}}),
                ui.ComboBox({"ID": 'marker_colors', }),
            ]),
            ui.Label({"StyleSheet": "max-height: 3px;"}),
            ui.Label({"StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"}),

            ui.HGroup({"Spacing": 5, "Weight": 0},[
                ui.Button({"ID": "split", "Text": "Do Durations", "Weight": 0, "Enabled": True}),
                ui.Label({"ID": 'status', "Text": "", "Alignment": {"AlignCenter": True}, 'ReadOnly': True}),
                ui.Label({"StyleSheet": "max-height: 5px;"}),
        ]),
    ])     
])

dlg = disp.AddWindow({ 
                        'WindowTitle': 'Marker to Marker Duration', 
                        'ID': 'MyWin',
                        'Geometry': [ 
                                    800, 500, # position when starting
                                    400, 150 # width, height
                         ], 
                        },
    window_01)
 
itm = dlg.GetItems()
itm['marker_colors'].AddItems(markercolor_names)


def _exit(ev):
    disp.ExitLoop()


def _split_timeline(marker_list):

    markers = _filter()

    current_timeline = bmd.scriptapp('Resolve').GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    tl_info = {
        'item': current_timeline,
        'name': str(current_timeline.GetName()),
        'fps': str(current_timeline.GetSetting('timelineFrameRate')),
        'drop': bool(int(current_timeline.GetSetting('timelineDropFrameTimecode'))),
        'in': int(current_timeline.GetStartFrame()),
        'out': int(current_timeline.GetEndFrame()),
    }
    tl_length = tl_info['out'] - tl_info['in']
    smpte = SMPTE()
    smpte.df = tl_info['drop']
    smpte.set_fps(tl_info['fps'])

    marked_frames = list(markers.keys())
    # Add timeline end
    marked_frames.append(tl_length) 

    for frameId in markers:
        dur = 1
        try:
            next_value = marked_frames[marked_frames.index(frameId) + 1]
            dur = next_value - marked_frames[marked_frames.index(frameId)]
            dur_tc = smpte.get_tc(dur)
        except:
            pass

        current_timeline.DeleteMarkerAtFrame(frameId)
        current_timeline.AddMarker(frameId, markers[frameId]['color'], markers[frameId]['name'], markers[frameId]['note'], dur, markers[frameId]['customData'])


def _filter(*ev):

    filter_color = bool(itm['split_by_color'].Checked)
    filtered_color = itm['marker_colors'].CurrentText
    if not filter_color:
        filtered_color = None

    current_timeline = bmd.scriptapp('Resolve').GetProjectManager().GetCurrentProject().GetCurrentTimeline()

    all_markers = current_timeline.GetMarkers()
    
    markers = {}
    if not filter_color or filtered_color is None:
        markers = all_markers
    else:
        markers = {}
        for k, v in all_markers.items():
            if v['color'] == filtered_color:
                markers[k] = v

    dlg.Find('status').Text = "{} markes found.".format(len(markers))

    return markers


dlg.On.MyWin.Close = _exit
dlg.On["split"].Clicked = _split_timeline
dlg.On['split_by_color'].Toggled = _filter
dlg.On['marker_colors'].CurrentIndexChanged = _filter

dlg.Show()
disp.RunLoop()
dlg.Hide()
