
#INPUT: 1. BACKGROUND.PNG (screenshot from mp4) 2.output from mad_score_movies.py (csv files)
#put all relevant files (one .png and all corresponding .csv) into one folder and call with dir.


#OUTPUT: /outputs/*.CSV -- ONE FILE PER ; t0=LASEROFF; dtarget=DISTANCE TO NEAREST TARGET

import argparse
import math
import glob
import os
import sys
import numpy as np
import pandas as pd
from pandas import Series
from pandas import DataFrame
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms

import roslib; roslib.load_manifest('flymad')
import flymad.flymad_analysis_dan as flymad_analysis
import flymad.flymad_plot as flymad_plot

#need to support numpy datetime64 types for resampling in pandas
assert np.version.version in ("1.7.1", "1.6.1")
assert pd.__version__ == "0.11.0"

def prepare_data(path, exp_genotype, exp2_genotype, ctrl_genotype):
    path_out = path + "/outputs/"


    # OPEN IMAGE of background  (.png)
    image_file = str(glob.glob(path + "/*.png"))[2:-2]
    image_file = open(image_file, 'r')
    image = plt.imread(image_file)
    fig1=plt.figure()
    fig1.set_size_inches(12,8)
    fig1.subplots_adjust(hspace=0)
    ax1=fig1.add_subplot(1,1,1)	
    #the original wide field camera was 659x494px. The rendered mp4 is 384px high
    #the widefield image is padded with a 10px margin, so it is technically 514 high.
    #scaling h=384->514 means new w=1371
    #
    #the image origin is top-left because matplotlib
    ax1.imshow(image, extent=[0,1371,514,0],zorder=0) #extent=[h_min,h_max,v_min,v_max]
    ax1.axis('off') 
    # DEFINE TARGET POSITIONS AND SAVE THEM TO A DATAFRAME (targets)    
    targets = []
    def onclick(target):
        #subtract 10px for the margin
        xydict = {'x': target.xdata-10, 'y': target.ydata-10}
        print xydict
        targets.append(xydict)
        return
    cid = fig1.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
    fig1.canvas.mpl_disconnect(cid)
    targets = DataFrame(targets)
    targets = (targets + 0.5).astype(int)
    if not os.path.exists(path_out):
        os.makedirs(path_out)
    targets.to_csv(path_out+'/targetlocations.csv')

    #PROCESS SCORE FILES:
    pooldf = DataFrame()
    filelist = []
    for df,metadata in flymad_analysis.courtship_combine_csvs_to_dataframe(sys.argv[1]):
        csvfilefn,experimentID,date,time,genotype,laser,repID = metadata

        #CALCULATE DISTANCE FROM TARGETs, KEEP MINIMUM AS dtarget
        dist = DataFrame.copy(df, deep=True)
        dist['x0'] = df['x'] - targets.ix[0,'x']
        dist['y0'] = df['y'] - targets.ix[0,'y']
        dist['x1'] = df['x'] - targets.ix[1,'x']
        dist['y1'] = df['y'] - targets.ix[1,'y']
        dist['x2'] = df['x'] - targets.ix[2,'x']
        dist['y2'] = df['y'] - targets.ix[2,'y']
        dist['x3'] = df['x'] - targets.ix[3,'x']
        dist['y3'] = df['y'] - targets.ix[3,'y']
        dist['d0'] = ((dist['x0'])**2 + (dist['y0'])**2)**0.5
        dist['d1'] = ((dist['x1'])**2 + (dist['y1'])**2)**0.5
        dist['d2'] = ((dist['x2'])**2 + (dist['y2'])**2)**0.5
        dist['d3'] = ((dist['x3'])**2 + (dist['y3'])**2)**0.5
        df['dtarget'] = dist.ix[:,'d0':'d3'].min(axis=1)               
        df = df.sort(columns='t', ascending=True, axis=0)
        
        #ALIGN BY LASER OFF TIME (=t0)
        if (df['as']==1).any():
            lasermask = df[df['as']==1]
            df['t'] = df['t'] - np.max(lasermask['t'].values)#laser off time =0               
        else:  
            print "No laser detected. Default start time = -120."
            df['t'] = df['t'] - np.min(df['t'].values) - 120
            continue  # throw out for now !!!!
             
        #bin to  5 second bins:
        df = df[np.isfinite(df['t'])]
        df['t'] = df['t'] /5
        df['t'] = df['t'].astype(int)
        df['t'] = df['t'].astype(float)
        df['t'] = df['t'] *5
        df = df.groupby(df['t'], axis=0).mean() 
        df['r'] = range(0,len(df))
        df['as'][df['as'] > 0] = 1
        df = df.set_index('r') 
        df['Genotype'] = genotype
        df['Genotype'][df['Genotype'] =='csGP'] = 'wGP'
        df['lasergroup'] = laser
        df['RepID'] = repID             

        df.to_csv((path_out + experimentID + "_" + date + ".csv"), index=False)
        pooldf = pd.concat([pooldf, df[['Genotype','lasergroup', 't','zx', 'dtarget', 'as']]])   

    # half-assed, uninformed danno's tired method of grouping for plots:
    expdf = pooldf[pooldf['Genotype'] == exp_genotype]
    exp2df = pooldf[pooldf['Genotype'] == exp2_genotype]
    ctrldf = pooldf[pooldf['Genotype']== ctrl_genotype]

    #we no longer need to group by genotype, and lasergroup is always the same here
    #so just drop it. 
    assert len(expdf['lasergroup'].unique()) == 1, "only one lasergroup handled"

    #Also ensure things are floats before plotting can fail, which it does because
    #groupby does not retain types on grouped colums, which seems like a bug to me

    expmean = expdf.groupby(['t'], as_index=False)[['zx', 'dtarget', 'as']].mean().astype(float)
    exp2mean = exp2df.groupby(['t'], as_index=False)[['zx', 'dtarget', 'as']].mean().astype(float)
    ctrlmean = ctrldf.groupby(['t'], as_index=False)[['zx', 'dtarget', 'as']].mean().astype(float)
    
    expstd = expdf.groupby(['t'], as_index=False)[['zx', 'dtarget', 'as']].std().astype(float)
    exp2std = exp2df.groupby(['t'], as_index=False)[['zx', 'dtarget', 'as']].std().astype(float)
    ctrlstd = ctrldf.groupby(['t'], as_index=False)[['zx', 'dtarget', 'as']].std().astype(float)
    
    expn = expdf.groupby(['t'],  as_index=False)[['zx', 'dtarget', 'as']].count().astype(float)
    exp2n = exp2df.groupby(['t'],  as_index=False)[['zx', 'dtarget', 'as']].count().astype(float)
    ctrln = ctrldf.groupby(['t'],  as_index=False)[['zx', 'dtarget', 'as']].count().astype(float)
    
    ####AAAAAAAARRRRRRRRRRRGGGGGGGGGGGGGGHHHHHHHHHH so much copy paste here
    expdf.save(path+'/exp.df')
    exp2df.save(path+'/exp2.df')
    ctrldf.save(path+'/ctrl.df')
    
    expmean.save(path+'/expmean.df')
    exp2mean.save(path+'/exp2mean.df')
    ctrlmean.save(path+'/ctrlmean.df')

    expstd.save(path+'/expstd.df')
    exp2std.save(path+'/exp2std.df')
    ctrlstd.save(path+'/ctrlstd.df')

    expn.save(path+'/expn.df')
    exp2n.save(path+'/exp2n.df')
    ctrln.save(path+'/ctrln.df')

    return (expdf, exp2df, ctrldf, expmean, exp2mean, ctrlmean, expstd, exp2std, ctrlstd, expn, exp2n, ctrln)

def load_data(path):

    return (
        pd.load(path+'/exp.df'),
        pd.load(path+'/exp2.df'),
        pd.load(path+'/ctrl.df'),
        pd.load(path+'/expmean.df'),
        pd.load(path+'/exp2mean.df'),
        pd.load(path+'/ctrlmean.df'),
        pd.load(path+'/expstd.df'),
        pd.load(path+'/exp2std.df'),
        pd.load(path+'/ctrlstd.df'),
        pd.load(path+'/expn.df'),
        pd.load(path+'/exp2n.df'),
        pd.load(path+'/ctrln.df')
    )


def plot_data(path, expdf, exp2df, ctrldf, expmean, exp2mean, ctrlmean, expstd, exp2std, ctrlstd, expn, exp2n, ctrln):
    path_out = path + "/outputs/"

    fig = plt.figure("Courtship Wingext 10min")
    ax = fig.add_subplot(1,1,1)

    flymad_plot.plot_timeseries_with_activation(ax,
                    exp=dict(xaxis=expmean['t'].values,
                             value=expmean['zx'].values,
                             std=expstd['zx'].values,
                             n=expn['zx'].values,
                             label='P1>TRPA1',
                             ontop=True),
                    ctrl=dict(xaxis=ctrlmean['t'].values,
                              value=ctrlmean['zx'].values,
                              std=ctrlstd['zx'].values,
                              n=ctrln['zx'].values,
                              label='Control'),
                    exp2=dict(xaxis=exp2mean['t'].values,
                             value=exp2mean['zx'].values,
                             std=exp2std['zx'].values,
                             n=exp2n['zx'].values,
                             label='pIP10>TRPA1',
                             ontop=True),
                    targetbetween=ctrlmean['as'].values>0,
                    sem=True,
    )

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Wing Ext. Index, +/- SEM')
    ax.set_title('Wing Extension', size=12)
    ax.set_ylim([-0.1,0.6])
    ax.set_xlim([-120,480])

    fig.savefig(flymad_plot.get_plotpath(path,"following_and_WingExt.png"), bbox_inches='tight')
    fig.savefig(flymad_plot.get_plotpath(path,"following_and_WingExt.svg"), bbox_inches='tight')

    if 0:
        fig = plt.figure("Courtship Dtarget 10min")
        ax = fig.add_subplot(1,1,1)

        flymad_plot.plot_timeseries_with_activation(ax,
                        exp=dict(xaxis=expmean['t'].values,
                                 value=expmean['zx'].values,
                                 std=expstd['zx'].values,
                                 n=expn['zx'].values,
                                 ontop=True),
                        ctrl=dict(xaxis=ctrlmean['t'].values,
                                  value=ctrlmean['dtarget'].values,
                                  std=ctrlstd['dtarget'].values,
                                  n=ctrln['dtarget'].values),
                        exp2=dict(xaxis=exp2mean['t'].values,
                                 value=exp2mean['dtarget'].values,
                                 std=exp2std['dtarget'].values,
                                 n=exp2n['dtarget'].values,
                                 ontop=True),
                        targetbetween=ctrlmean['as'].values>0,
                        sem=True,
        )

        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Distance (pixels), +/- SEM')
        ax.set_title('Distance to Nearest Target', size=12)
        ax.set_ylim([20,120])
        ax.set_xlim([-120,480])

        fig.savefig(flymad_plot.get_plotpath(path,"following_and_dtarget.png"), bbox_inches='tight')
        fig.savefig(flymad_plot.get_plotpath(path,"following_and_dtarget.svg"), bbox_inches='tight')

if __name__ == "__main__":
    CTRL_GENOTYPE = 'uasstoptrpmyc' #black
    EXP_GENOTYPE = 'wGP' #blue
    EXP_GENOTYPE2 = '40347' #purple

    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs=1, help='path to csv files')
    parser.add_argument('--only-plot', action='store_true', default=False)
    parser.add_argument('--show', action='store_true', default=False)

    args = parser.parse_args()
    path = args.path[0]

    if args.only_plot:
        data = load_data(path)
    else:
        data = prepare_data(path, EXP_GENOTYPE, EXP_GENOTYPE2, CTRL_GENOTYPE)

    plot_data(path, *data)

    if args.show:
        plt.show()

