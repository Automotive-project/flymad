#!/usr/bin/env python
import pandas as pd
import sys, os,re
import glob
import numpy as np
import matplotlib.pyplot as plt
import time
import collections

import madplot

from th_experiments import DOROTHEA_NAME_RE_BASE, DOROTHEA_BAGDIR
DOROTHEA_NAME_REGEXP = re.compile(r'^' + DOROTHEA_NAME_RE_BASE + '.mp4.csv$')
BAG_DATE_FMT = "%Y-%m-%d-%H-%M-%S.bag"

Scored = collections.namedtuple('Scored', 'bag csv')

def load_bagfile_get_laseron(arena, score, smooth):
    NO_PROBOSCIS = 0
    PROBOSCIS = 1

    NO_WING_MOVEMENTS = 0
    WING_MOVEMENTS = 1

    NO_JUMPING = 0
    JUMPING = 1

    l_df, t_df, h_df, geom = madplot.load_bagfile(score.bag, arena, smooth=smooth)

    proboscis_scored_ix = [t_df.index[0]]
    proboscis_scored_v = [NO_PROBOSCIS]

    wing_scored_ix = [t_df.index[0]]
    wing_scored_v = [NO_WING_MOVEMENTS]

    jump_scored_ix = [t_df.index[0]]
    jump_scored_v = [NO_JUMPING]

    score_df = pd.read_csv(score.csv)

    for idx,row in score_df.iterrows():
        csv_row_frame = row['framenumber']
        if np.isnan(csv_row_frame):
            continue

        matching = t_df[t_df['t_framenumber'] == int(csv_row_frame)]
        if len(matching) ==1:

            # proboscis ---------------
            proboscis_scored_ix.append(matching.index[0])
            rowval = row['as']
            if rowval=='a':
                proboscis_scored_v.append( PROBOSCIS )
            elif rowval=='s':
                proboscis_scored_v.append( NO_PROBOSCIS )
            elif np.isnan(rowval):
                #proboscis_scored_v.append( NO_PROBOSCIS )
                proboscis_scored_v.append(np.nan)
            else:
                raise ValueError('unknown row value: %r'%rowval)


            # wing ---------------
            wing_scored_ix.append(matching.index[0])
            rowval = row['zx']
            if rowval=='z':
                wing_scored_v.append( WING_MOVEMENTS )
            elif rowval=='x':
                wing_scored_v.append( NO_WING_MOVEMENTS )
            elif np.isnan(rowval):
                #wing_scored_v.append( NO_WING_MOVEMENTS )
                wing_scored_v.append(np.nan)
            else:
                raise ValueError('unknown row value: %r'%rowval)

            # jump ---------------
            jump_scored_ix.append(matching.index[0])
            rowval = row['cv']
            if rowval=='c':
                jump_scored_v.append( JUMPING )
            elif rowval=='v':
                jump_scored_v.append( NO_JUMPING )
            elif np.isnan(rowval):
                #jump_scored_v.append( NO_JUMPING )
                jump_scored_v.append(np.nan)
            else:
                raise ValueError('unknown row value: %r'%rowval)

        else:
            print "len(matching)",len(matching)
            # why would we ever get here?
            1/0

    s = pd.Series(proboscis_scored_v,index=proboscis_scored_ix)
    t_df['proboscis'] = s

    s = pd.Series(wing_scored_v,index=wing_scored_ix)
    t_df['wing'] = s

    s = pd.Series(jump_scored_v,index=jump_scored_ix)
    t_df['jump'] = s

    t_df['proboscis'].fillna(method='ffill', inplace=True)
    t_df['wing'].fillna(method='ffill', inplace=True)
    t_df['jump'].fillna(method='ffill', inplace=True)
#    t_df['Vfwd'] = t_df['v'] * t_df['fwd']

    lon = l_df[l_df['laser_power'] > 0]

    if len(lon):
        ton = lon.index[0]

        l_off_df = l_df[ton:]
        loff = l_off_df[l_off_df['laser_power'] == 0]
        toff = loff.index[0]

        onoffset = np.where(t_df.index >= ton)[0][0]
        offoffset = np.where(t_df.index >= toff)[0][0]

        return t_df, onoffset

    else:
        return None, None

def get_bagfilename( bag_dirname, dtval ):
    MP4_DATE_FMT = "%Y%m%d_%H%M%S"
    mp4time = time.strptime(dtval, MP4_DATE_FMT)

    inputbags = glob.glob( os.path.join(bag_dirname,'*.bag') )
    best_diff = np.inf
    bname = None
    for bag in inputbags:
        bagtime = time.strptime(os.path.basename(bag), BAG_DATE_FMT)
        this_diff = abs(time.mktime(bagtime)-time.mktime(mp4time))
        if this_diff < best_diff:
            bname = bag
            best_diff = this_diff
        else:
            continue
    if best_diff > 10.0:
        raise RuntimeError( 'no bagfile found for %s'%dtval)
    assert os.path.exists(bname)
    return bname


def my_subplot( n_conditions ):
    if n_conditions==0:
        n_rows, n_cols = 1,1
    elif n_conditions==1:
        n_rows, n_cols = 1,1
    elif n_conditions==2:
        n_rows, n_cols = 2,1
    elif n_conditions==3:
        n_rows, n_cols = 2,2
    elif n_conditions==4:
        n_rows, n_cols = 2,2
    elif n_conditions==5:
        n_rows, n_cols = 3,2
    elif n_conditions==6:
        n_rows, n_cols = 3,2
    elif n_conditions==7:
        n_rows, n_cols = 3,3
    elif n_conditions==8:
        n_rows, n_cols = 3,3
    elif n_conditions==9:
        n_rows, n_cols = 3,3
    else:
        print 'n_conditions',n_conditions
        1/0
    return n_rows, n_cols

dirname = sys.argv[1]
if 1:
    dfs = collections.defaultdict(list)
    csv_files = glob.glob( os.path.join(dirname,'csvs','*.csv') )
    bag_dirname = os.path.join(dirname,'bags')
    for csv_filename in csv_files:
        matchobj = DOROTHEA_NAME_REGEXP.match(os.path.basename(csv_filename))
        if matchobj is None:
            print "error: incorrectly named file?", csv_filename
            continue

        #print csv_filename
        parsed_data = matchobj.groupdict()
        parsed_data['condition'] = parsed_data['condition'].lower()
        #print parsed_data
#        if int(parsed_data['trialnum'])!=2:
#            print "parsed_data['trialnum']",parsed_data['trialnum']
#            continue
        #print 'parsed_data',parsed_data
        #print 'CSV datetime',parsed_data['datetime']
        bag_filename = get_bagfilename( bag_dirname, parsed_data['datetime'] )
        arena = madplot.Arena('mm')


        smooth=True
#        smooth=False


#        l_df, t_df, h_df, geom = madplot.load_bagfile(bag_filename, arena, smooth=smooth)
        score = Scored(bag_filename, csv_filename)
        t_df,lon = load_bagfile_get_laseron(arena, score, smooth)
        assert t_df is not None

        # y = dataframe['as'].values
        # print y.dtype
        # x = np.arange( len(y) )
        # plt.plot(x,y,label='%s'%(parsed_data['condition'],))
        dfs[parsed_data['condition']].append( (t_df, parsed_data) )
    conditions = dfs.keys()
    n_conditions = len(conditions)
    for measurement in ['proboscis',
                        'wing',
                        'jump']:
        fig = plt.figure(measurement)
        n_rows, n_cols = my_subplot( n_conditions )
        for i, condition in enumerate(conditions):
            ax = fig.add_subplot(n_rows, n_cols, i+1 )
            arrs = []
            for (t_df,parsed_data) in dfs[condition]:
                ax.plot(t_df[measurement],
                        label='%s (fly %s, trial %s)'%(parsed_data['condition'],
                                                       parsed_data['condition_flynum'],
                                                       parsed_data['trialnum'],
                                                       ))
                arrs.append( t_df['proboscis'] )
            all_arrs = np.array( arrs )
            mean_arr = np.mean( all_arrs, axis=0 )
            ax.plot( mean_arr, color='k', lw=2 )
            ax.set_title('%s (n=%d)'%(condition, len(dfs[condition])))
            #ax.legend()
    plt.show()
