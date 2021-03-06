import os
import shutil
import glob
import pandas as pd
import numpy as np
from nipype.interfaces.fsl import Merge
from nipype.interfaces import fsl
from subprocess import call
from nipype.interfaces.fsl import MultipleRegressDesign
from scipy.stats import zscore
import argparse



parser = argparse.ArgumentParser(description='Run Second Level Results for DR Resting State Networks')
parser.add_argument('-rwr', help='Option to run with Randomise',required=False,default=True,type=int)
parser.add_argument('-rwf', help='Option to run with FLAME',required=False,default=False,type=int)
parser.add_argument('-n',help='Number of Permutations to Run', required=False,default=10000,type=int)
parser.add_argument('-r1samp', help='Option to run 1 sample t-test',required=False,default=True,type=int)
parser.add_argument('-rpair', help='Option to run paired t-test',required=False,default=True,type=int)
parser.add_argument('-rall', help='Option to run all subjects or good motion subjects',required=False,default=1,type=int)
parser.add_argument('-rsn', help='List of Resting-State netorks to run',nargs='+', type=int,required=False,default=[3])
parser.add_argument('-a', help='Option to add subject age to model',required=False,default=0,type=int)
parser.add_argument('-g', help='Option to add subject gender to model',required=False,default=0,type=int)
parser.add_argument('-gmThresh',help='Grey Matter Threshold Value',default=0.2,type=float,required=False)
parser.add_argument('-perfThreshold', help='Value for Performance Threshold)',required=False,default=15,type=int)
args = parser.parse_args()


#Decide if running all subjects or just good subjects
runWithRandomise =args.rwr
runFlame= args.rwf
nperms=args.n
runPair=args.rpair
run1Sample=args.r1samp
runAll=args.rall
addScanOrder=False
rsn=args.rsn
# runWithRandomise = True
# nperms=10000
# runPair=True
# run1Sample=True
runPairNew=False
# #Decide if running all subjects or just good subjects
# runAll=True
age=args.a
gender=args.g
#if run with performance
runWithPerformance=False
perfThreshold=args.perfThreshold

gmThresh=args.gmThresh

mask_name='/home/jmuraskin/Projects/CCD/working_v1/seg_probabilities/grey_matter_mask-%d-percent.nii.gz' % int(gmThresh*100)



def getSubjectButtonResponses():
    filelist=pd.read_csv('/home/jmuraskin/Projects/CCD/CCD-scripts/NARSAD_stimulus_JM.csv')

    for indx,f in enumerate(filelist['JM_INTERNAL']):
        for r in range(1,3):
            if int(f[-2:])<30:
                luminaFlag=0
            else:
                luminaFlag=1
            numberofbuttonPresses=getSubjectButtonPressScore('/home/jmuraskin/Projects/CCD/NARSAD-DMN-clean/%s_run%d.txt' % (f,r),luminaFlag)
            out={'number':numberofbuttonPresses,'filename':f}
            out['filename']=f
            if (indx+r)==1:
                df=pd.DataFrame(out,index=[0])
                df['subject']=f
                df['run']=r
            else:
                tmp=pd.DataFrame(out,index=[0])
                tmp['subject']=f
                tmp['run']=r
                df=pd.concat((df,tmp),ignore_index=0)
    return df


def getSubjectButtonPressScore(filename,luminaFlag):
    config=pd.read_table(filename,delimiter=';',comment='#')
    numButton=0
    for indx in config[config[' Stim Text']==' Push Button'].index[:]:
        numTmp=0
        for n in range(5):
            if luminaFlag:
                if config.iloc[indx+n][' STIM']==' LUMINA' and numTmp==0:
                    numButton+=1
                    numTmp+=1
            else:
                if config.iloc[indx+n][' STIM']!='53' and numTmp==0:
                    numButton+=1
                    numTmp+=1
    return numButton


if not os.path.exists(mask_name):
    from nilearn.image import threshold_img
    mask_img=threshold_img('/home/jmuraskin/Projects/CCD/working_v1/seg_probabilities/grey_matter_mask.nii.gz',threshold=gmThresh)
    mask_img_data=mask_img.get_data()
    mask_img_data[mask_img_data>0]=1
    mask_img=new_img_like(mask_img,mask_img_data)
    mask_img.to_filename(mask_name)


def subjectinfo(subject_id,getFeedback=True):
    #Get whether scan is a feedback scan or not
    from pandas import read_csv

    SubjInfo = read_csv('/home/jmuraskin/Projects/CCD/CCD-scripts/NARSAD_stimulus_JM.csv')
    SubjInfo.set_index('JM_INTERNAL',inplace=True)
    scan1=SubjInfo.loc[subject_id]['SCAN_1_FEEDBACK']
    if scan1:
        feedback=0
        noFeedback=1
    else:
        feedback=1
        noFeedback=0
    if getFeedback:
        return feedback+1
    if not getFeedback:
        return noFeedback+1



#load subject list
motionTest=pd.read_csv('/home/jmuraskin/Projects/CCD/CCD-scripts/analysis/CCD_meanFD.csv')
performance=pd.read_csv('/home/jmuraskin/Projects/CCD/CCD-scripts/analysis/CCD_performance.csv',names=['Subject_ID','FB','scanorder','R'])
fbNames=['NOFEEDBACK','FEEDBACK','TRAIN']

if runAll==1:
    subject_list=np.unique(motionTest.Subject_ID)
    motionDir='all'
elif runAll==2:
    depressed=np.array(['CCD072','CCD098','CCD083','CCD062','CCD061','CCD051','CCD087'])
    poor_performers=np.array(['CCD094','CCD075','CCD086','CCD080','CCD076','CCD065','CCD034'])
    motionThresh=1
    allsubj=np.unique(motionTest['Subject_ID'])
    motionReject=np.unique((motionTest[motionTest.Max_Relative_RMS_Displacement>motionThresh]['Subject_ID']))
    subject_list=np.setdiff1d(np.setdiff1d(np.setdiff1d(allsubj,motionReject),depressed),poor_performers)
    motionDir='motionRMS-%f' % motionThresh

elif runAll==3:
    #Reject Depressed subjects
    depressed=np.array(['CCD072','CCD098','CCD083','CCD062','CCD061','CCD051','CCD087'])

    df=getSubjectButtonResponses()
    tmp=df.groupby('subject')['number'].sum()
    poor_performers=np.array(tmp[tmp<perfThreshold].index[:])


    motionThresh=1
    allsubj=np.unique(motionTest['Subject_ID'])
    motionReject=np.unique((motionTest[motionTest.Max_Relative_RMS_Displacement>motionThresh]['Subject_ID']))
    subject_list=np.setdiff1d(np.setdiff1d(np.setdiff1d(allsubj,motionReject),depressed),poor_performers)
    motionDir='motionRMS-%f-subjperf-%d' % (motionThresh,perfThreshold)
else:
    motionThresh=0.2
    allsubj=np.unique(motionTest['Subject_ID'])
    motionReject=np.unique((motionTest[motionTest.meanFD>motionThresh]['Subject_ID']))
    subject_list=np.setdiff1d(allsubj,motionReject)
    motionDir='motionThresh-%f' % motionThresh

#load phenotypic data
phenoFile='/home/jmuraskin/Projects/CCD/Pheno/narsad+vt_new.csv'
pheno=pd.read_csv(phenoFile)
pheno=pheno.set_index('participant')
if age:
    ages=zscore(pheno.loc[subject_list]['V1_DEM_001'])
if gender:
    mf=zscore(pheno.loc[subject_list]['V1_DEM_002'])



for RSN in rsn:

    #create second level folders
    folderbase='/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/RSN%d/' % RSN



    if not os.path.exists(folderbase):
        os.mkdir(folderbase)

    pairedFolder= folderbase + 'paired/'

    if not os.path.exists(pairedFolder):
        os.mkdir(pairedFolder)

    pairedFolder= pairedFolder + motionDir

    if not os.path.exists(pairedFolder):
        os.mkdir(pairedFolder)

    meanFBFolder=folderbase + 'meanFB'
    if not os.path.exists(meanFBFolder):
        os.mkdir(meanFBFolder)

    meanNFBFolder=folderbase + 'meanNFB'
    if not os.path.exists(meanNFBFolder):
        os.mkdir(meanNFBFolder)

    meanTrainFolder=folderbase + 'train'
    if not os.path.exists(meanTrainFolder):
        os.mkdir(meanTrainFolder)

    meanFBFolder=meanFBFolder + '/' + motionDir
    meanNFBFolder=meanNFBFolder + '/' + motionDir
    meanTrainFolder=meanTrainFolder + '/' + motionDir

    if not os.path.exists(meanFBFolder):
        os.mkdir(meanFBFolder)

    if not os.path.exists(meanNFBFolder):
        os.mkdir(meanNFBFolder)

    if not os.path.exists(meanTrainFolder):
        os.mkdir(meanTrainFolder)

    if runWithPerformance:
        meanFBFolder=meanFBFolder+'/performance'

        if not os.path.exists(meanFBFolder):
            os.mkdir(meanFBFolder)

        meanNFBFolder=meanNFBFolder+'/performance'

        if not os.path.exists(meanNFBFolder):
            os.mkdir(meanNFBFolder)

        meanTrainFolder=meanTrainFolder+'/performance'

        if not os.path.exists(meanTrainFolder):
            os.mkdir(meanTrainFolder)



    if run1Sample:
        for fb in [0,1,2]:
            x=[]
            for subj in subject_list:
                if fb<2:
                    fbLoc=subjectinfo(subj,fb)
                    fname= '/home/jmuraskin/Projects/CCD/CPAC-out/pipeline_CCD_v1/%s_data_/dr_tempreg_maps_files_to_standard_smooth/_scan_feedback_%d/_csf_threshold_0.96/_gm_threshold_0.7/_wm_threshold_0.96/_compcor_ncomponents_5_selector_pc10.linear1.wm0.global0.motion1.quadratic1.gm0.compcor1.csf1/_spatial_map_PNAS_Smith09_rsn10/_fwhm_6/_dr_tempreg_maps_files_smooth_0%d/temp_reg_map_000%d_antswarp_maths.nii.gz' % (subj,fbLoc,RSN,RSN)
                else:
                    fname= '/home/jmuraskin/Projects/CCD/CPAC-out/pipeline_CCD_v1/%s_data_/dr_tempreg_maps_files_to_standard_smooth/_scan_tra/_csf_threshold_0.96/_gm_threshold_0.7/_wm_threshold_0.96/_compcor_ncomponents_5_selector_pc10.linear1.wm0.global0.motion1.quadratic1.gm0.compcor1.csf1/_spatial_map_PNAS_Smith09_rsn10/_fwhm_6/_dr_tempreg_maps_files_smooth_0%d/temp_reg_map_000%d_antswarp_maths.nii.gz' % (subj,RSN,RSN)
                # fname = '/home/jmuraskin/Projects/CCD/CPAC-out/pipeline_CCD_v1/%s_data_/dr_tempreg_maps_files_to_standard_smooth/_scan_feedback_%d/%s%d.nii.gz' % (fbLoc,subj,t,i)
                x.append(fname)
            subjs = len(x)
            merger = Merge()
            merger.inputs.in_files = x
            merger.inputs.dimension = 't'
            merger.inputs.output_type = 'NIFTI_GZ'
            merger.inputs.merged_file = './DMN_merged_%s.nii.gz' % fbNames[fb]
            merger.run()
            #get meanFD values for each subject and add as covariate
            if fb<2:
                meanFD=zscore(motionTest[motionTest.FB==fbNames[fb]][motionTest.Subject_ID.isin(subject_list)]['meanFD'])
            else:
                meanFD=zscore(motionTest[motionTest.FB==fbNames[0]][motionTest.Subject_ID.isin(subject_list)]['train_meanFD'])
            model = MultipleRegressDesign()
            model.inputs.contrasts = [['group mean', 'T',['reg1'],[1]],['group neg mean', 'T',['reg1'],[-1]]]
            regressors=dict(reg1=[1]*len(subject_list),FD=list(meanFD))
            if age:
                regressors['age']=list(ages)
            if gender:
                regressors['mf']=list(mf)
            model.inputs.regressors = regressors
            model.run()


            if runWithRandomise:
                os.mkdir(fbNames[fb])
                if not os.path.exists(fbNames[fb]):
                    os.mkdir(fbNames[fb])
                os.system('mv ./design.* ./%s' % fbNames[fb])
                shutil.move('DMN_merged_%s.nii.gz' % fbNames[fb],'./%s' % fbNames[fb])
                randomiseCommand='/home/jmuraskin/Projects/CCD/CCD-scripts/analysis/randomise_forpython.sh -i %s -o ./%s/fb -d ./%s/design.mat -t ./%s/design.con -e ./%s/design.grp -m %s -T -n %d' % ('./%s/DMN_merged_%s.nii.gz' % (fbNames[fb],fbNames[fb]),fbNames[fb],fbNames[fb],fbNames[fb],fbNames[fb],mask_name,nperms)
                os.system(randomiseCommand)

                if fb == 1:
                    foldername=meanFBFolder
                elif fb == 2:
                    foldername=meanTrainFolder
                else:
                    foldername=meanNFBFolder

                filename=fbNames[fb]

                print 'Making folder: %s' % foldername
                if not os.path.exists(foldername):
                    os.mkdir(foldername)

                if os.path.exists(os.path.join(foldername,filename)):
                    shutil.rmtree(os.path.join(foldername,filename))

                shutil.move(filename,os.path.join(foldername,filename))

    if runPair:

        # First Run Paired Difference between FB-NoFB
        pairedmodel = MultipleRegressDesign()
        pairedmodel.inputs.contrasts = [['A>B', 'T',['reg1'],[1]],['B>A', 'T',['reg1'],[-1]]]
        if runFlame:
            pairedmodel.inputs.groups = [1]*len(subject_list)*2
        else:
            pairedmodel.inputs.groups = range(1,len(subject_list)+1) + range(1,len(subject_list)+1)
        #make paired ttest model
        modelX=[0]*2*len(subject_list)
        modelXAB=modelX
        modelXAB[0:len(subject_list)]=[1]*len(subject_list)
        modelDict=dict(reg1=modelXAB)
        for indx,subj in enumerate(subject_list):
            modeltmp=[0]*2*len(subject_list)
            modeltmp[indx]=1
            modeltmp[indx+len(subject_list)]=1
            modelDict['s%d' % indx]= modeltmp

        modelDict['FD'] = list(zscore(list(motionTest[motionTest.FB=='FEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['meanFD'])
        + list(motionTest[motionTest.FB=='NOFEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['meanFD'])))
        if addScanOrder:
            modelDict['scanorder']= list(zscore(list(motionTest[motionTest.FB=='FEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['scanorder'])
        + list(motionTest[motionTest.FB=='NOFEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['scanorder'])))
        if age:
            modelDict['age']=list(ages)+list(ages)
        if gender:
            modelDict['mf']=list(mf)+list(mf)
        pairedmodel.inputs.regressors = modelDict
        pairedmodel.run()

        x=[meanFBFolder + '/' + fbNames[1] + '/DMN_merged_FEEDBACK.nii.gz',\
        meanNFBFolder + '/' + fbNames[0] + '/DMN_merged_NOFEEDBACK.nii.gz']
        fslMathsCommand='fslmerge -t DMN_pair_merged %s %s' % (x[0],x[1])
        os.system(fslMathsCommand)
        filename='RSN_pair_FB_NFB'
        if not os.path.exists(filename):
            os.mkdir(filename)
        os.system('mv ./design.* ./RSN_pair_FB_NFB')
        os.system('mv ./DMN_pair_merged.nii.gz ./RSN_pair_FB_NFB')
        randomiseCommand='/home/jmuraskin/Projects/CCD/CCD-scripts/analysis/randomise_forpython.sh -i %s -o ./RSN_pair_FB_NFB/paired -d ./RSN_pair_FB_NFB/design.mat -t ./RSN_pair_FB_NFB/design.con -e ./RSN_pair_FB_NFB/design.grp -m %s -T -n %d' % ('./RSN_pair_FB_NFB/DMN_pair_merged.nii.gz',mask_name,nperms)
        os.system(randomiseCommand)

        foldername=pairedFolder
        if os.path.exists(os.path.join(foldername,filename)):
            shutil.rmtree(os.path.join(foldername,filename))

        shutil.move(filename,os.path.join(foldername,filename))
        # shutil.move('RSN_pair_FB_NFB',pairedFolder + '/RSN_pair_FB_NFB')


        # Second Run Paired Difference between FB-Rest
        pairedmodel = MultipleRegressDesign()
        pairedmodel.inputs.contrasts = [['A>B', 'T',['reg1'],[1]],['B>A', 'T',['reg1'],[-1]]]
        if runFlame:
            pairedmodel.inputs.groups = [1]*len(subject_list)*2
        else:
            pairedmodel.inputs.groups = range(1,len(subject_list)+1) + range(1,len(subject_list)+1)
        #make paired ttest model
        modelX=[0]*2*len(subject_list)
        modelXAB=modelX
        modelXAB[0:len(subject_list)]=[1]*len(subject_list)
        modelDict=dict(reg1=modelXAB)
        for indx,subj in enumerate(subject_list):
            modeltmp=[0]*2*len(subject_list)
            modeltmp[indx]=1
            modeltmp[indx+len(subject_list)]=1
            modelDict['s%d' % indx]= modeltmp

        modelDict['FD'] = list(zscore(list(motionTest[motionTest.FB=='FEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['meanFD'])
        + list(motionTest[motionTest.FB=='NOFEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['train_meanFD'])))

        if age:
            modelDict['age']=list(ages)+list(ages)
        if gender:
            modelDict['mf']=list(mf)+list(mf)
        pairedmodel.inputs.regressors = modelDict
        pairedmodel.run()

        x=[meanFBFolder + '/' + fbNames[1] + '/DMN_merged_FEEDBACK.nii.gz',\
        meanTrainFolder + '/' + fbNames[2] + '/DMN_merged_TRAIN.nii.gz']
        fslMathsCommand='fslmerge -t DMN_pair_merged %s %s' % (x[0],x[1])
        os.system(fslMathsCommand)
        filename='RSN_pair_FB_TRAIN'
        if not os.path.exists(filename):
            os.mkdir(filename)
        os.system('mv ./design.* ./RSN_pair_FB_TRAIN')
        os.system('mv ./DMN_pair_merged.nii.gz ./RSN_pair_FB_TRAIN')
        randomiseCommand='/home/jmuraskin/Projects/CCD/CCD-scripts/analysis/randomise_forpython.sh -i %s -o ./RSN_pair_FB_TRAIN/paired -d ./RSN_pair_FB_TRAIN/design.mat -t ./RSN_pair_FB_TRAIN/design.con -e ./RSN_pair_FB_TRAIN/design.grp -m %s -T -n %d' % ('./RSN_pair_FB_TRAIN/DMN_pair_merged.nii.gz',mask_name,nperms)
        os.system(randomiseCommand)

        foldername=pairedFolder
        if os.path.exists(os.path.join(foldername,filename)):
            shutil.rmtree(os.path.join(foldername,filename))

        shutil.move(filename,os.path.join(foldername,filename))


        # Second Run Paired Difference between FB-Rest
        pairedmodel = MultipleRegressDesign()
        pairedmodel.inputs.contrasts = [['A>B', 'T',['reg1'],[1]],['B>A', 'T',['reg1'],[-1]]]
        if runFlame:
            pairedmodel.inputs.groups = [1]*len(subject_list)*2
        else:
            pairedmodel.inputs.groups = range(1,len(subject_list)+1) + range(1,len(subject_list)+1)
        #make paired ttest model
        modelX=[0]*2*len(subject_list)
        modelXAB=modelX
        modelXAB[0:len(subject_list)]=[1]*len(subject_list)
        modelDict=dict(reg1=modelXAB)
        for indx,subj in enumerate(subject_list):
            modeltmp=[0]*2*len(subject_list)
            modeltmp[indx]=1
            modeltmp[indx+len(subject_list)]=1
            modelDict['s%d' % indx]= modeltmp

        modelDict['FD'] = list(zscore(list(motionTest[motionTest.FB=='NOFEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['meanFD'])
        + list(motionTest[motionTest.FB=='NOFEEDBACK'][motionTest.Subject_ID.isin(subject_list)]['train_meanFD'])))

        if age:
            modelDict['age']=list(ages)+list(ages)
        if gender:
            modelDict['mf']=list(mf)+list(mf)
        pairedmodel.inputs.regressors = modelDict
        pairedmodel.run()

        x=[meanNFBFolder + '/' + fbNames[0] + '/DMN_merged_NOFEEDBACK.nii.gz',\
        meanTrainFolder + '/' + fbNames[2] + '/DMN_merged_TRAIN.nii.gz']
        fslMathsCommand='fslmerge -t DMN_pair_merged %s %s' % (x[0],x[1])
        os.system(fslMathsCommand)

        filename='RSN_pair_NFB_TRAIN'
        if not os.path.exists(filename):
            os.mkdir(filename)
        os.system('mv ./design.* ./RSN_pair_NFB_TRAIN')
        os.system('mv ./DMN_pair_merged.nii.gz ./RSN_pair_NFB_TRAIN')
        randomiseCommand='/home/jmuraskin/Projects/CCD/CCD-scripts/analysis/randomise_forpython.sh -i %s -o ./RSN_pair_NFB_TRAIN/paired -d ./RSN_pair_NFB_TRAIN/design.mat -t ./RSN_pair_NFB_TRAIN/design.con -e ./RSN_pair_NFB_TRAIN/design.grp -m %s -T -n %d' % ('./RSN_pair_NFB_TRAIN/DMN_pair_merged.nii.gz',mask_name,nperms)
        os.system(randomiseCommand)


        foldername=pairedFolder
        if os.path.exists(os.path.join(foldername,filename)):
            shutil.rmtree(os.path.join(foldername,filename))

        shutil.move(filename,os.path.join(foldername,filename))
