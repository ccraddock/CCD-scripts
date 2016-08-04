import os
import shutil
import glob
from nipype.interfaces.fsl import Merge
from nipype.interfaces import fsl
from subprocess import call


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
        return feedback
    if not getFeedback:
        return noFeedback

#Create subject list
CCD_numbers=[12,14,15,16,17,18,20,21,22,27,32,33,34,35,40,42,51,52,59,60,61,63,64,65,66,67,73,74,75,76,81,83,85,88,89,91,93,95,97,98,99]

subject_list=[]
for ccd in CCD_numbers:
    subject_list.append('CCD0%s' % ccd)
#
secondlevel_folder_names=['noFeedback','Feedback']

runWithRandomise = True
nperms=5000
runPair=True
run1Sample=False
#

if runWithRandomise:
    if run1Sample:
        for i in range(1,6):
            for fb in [0,1]:
                for t in ['cope']:
                    x=[]
                    for subj in subject_list:
                        fbLoc=subjectinfo(subj,fb)
                        fname = '/home/jmuraskin/Projects/CCD/working_v1/feedback_run-%d/feedback/_subject_id_%s/modelestimate/mapflow/_modelestimate0/results/%s%d.nii.gz' % (fbLoc,subj,t,i)
                        x.append(fname)
                    subjs = len(x)
                    merger = Merge()
                    merger.inputs.in_files = x
                    merger.inputs.dimension = 't'
                    merger.inputs.output_type = 'NIFTI_GZ'
                    # merger.inputs.merged_file = './cope' + str(i) + '_tfce_merged'
                    merger.run()

                if os.path.exists('./stats'):
                    shutil.rmtree('./stats')
                os.mkdir('./stats')

                randomiseCommand='./randomise_forpython.sh -i %s -o ./stats/cope%d -1 -m %s -T -n %d' % ('cope' + str(i) + '_merged.nii.gz',i,'/usr/share/fsl/5.0/data/standard/MNI152_T1_3mm_brain_mask.nii.gz',nperms)
                print randomiseCommand
                os.system(randomiseCommand)

                foldername='/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/randomise/' + secondlevel_folder_names[fb] + '/cope' + str(i)
                if os.path.exists(foldername):
                    shutil.rmtree(foldername)
                    os.mkdir(foldername)
                else:
                    os.mkdir(foldername)
                shutil.move('cope' + str(i) + '_merged.nii.gz',foldername)
                shutil.move('stats',foldername)
    if runPair:
        for i in range(1,6):
            for t in ['cope']:

                subtractCopes =  fsl.maths.MultiImageMaths()
                subtractCopes.inputs.op_string = "-sub %s"
                subtractCopes.inputs.in_file = '/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/randomise/Feedback/cope' + str(i) + '/' + t + str(i) + '_merged.nii.gz'
                subtractCopes.inputs.operand_files = ['/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/randomise/noFeedback/cope' + str(i) + '/' +t + str(i) + '_merged.nii.gz']
                subtractCopes.inputs.out_file = 'copediff_FB_gt_nFB_merged.nii.gz'
                subtractCopes.run()

                subtractCopes =  fsl.maths.MultiImageMaths()
                subtractCopes.inputs.op_string = "-sub %s"
                subtractCopes.inputs.in_file = '/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/randomise/noFeedback/cope' + str(i) + '/' + t + str(i) + '_merged.nii.gz'
                subtractCopes.inputs.operand_files = ['/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/randomise/Feedback/cope' + str(i) + '/' +t + str(i) + '_merged.nii.gz']
                subtractCopes.inputs.out_file = 'copediff_nFB_gt_FB_merged.nii.gz'
                subtractCopes.run()

            os.mkdir('stats_FB_gt_nFB')
            randomiseCommand='./randomise_forpython.sh -i %s -o ./stats_FB_gt_nFB/cope%d -1 -m %s -T -n %d' % ('copediff_FB_gt_nFB_merged.nii.gz',i,'/usr/share/fsl/5.0/data/standard/MNI152_T1_3mm_brain_mask.nii.gz',nperms)
            os.system(randomiseCommand)
            os.mkdir('stats_nFB_gt_FB')
            randomiseCommand='./randomise_forpython.sh -i %s -o ./stats_nFB_gt_FB/cope%d -1 -m %s -T -n %d' % ('copediff_nFB_gt_FB_merged.nii.gz',i,'/usr/share/fsl/5.0/data/standard/MNI152_T1_3mm_brain_mask.nii.gz',nperms)
            os.system(randomiseCommand)


            foldername='/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/randomise/paired-Ttest/cope' + str(i)
            if os.path.exists(foldername):
                shutil.rmtree(foldername)
                os.mkdir(foldername)
            else:
                os.mkdir(foldername)
            shutil.move('copediff_FB_gt_nFB_merged.nii.gz',foldername)
            shutil.move('copediff_nFB_gt_FB_merged.nii.gz',foldername)
            shutil.move('stats_FB_gt_nFB',foldername)
            shutil.move('stats_nFB_gt_FB',foldername)


else:

    if run1Sample:
        from nipype.interfaces.fsl import MultipleRegressDesign
        model = MultipleRegressDesign()
        model.inputs.contrasts = [['group mean', 'T',['reg1'],[1]]]
        model.inputs.regressors = dict(reg1=[1]*len(CCD_numbers))
        model.run()

        for i in range(1,6):
            for fb in [0,1]:
                for t in ['cope', 'varcope']:
                    x=[]
                    for subj in subject_list:
                        fbLoc=subjectinfo(subj,fb)
                        fname = '/home/jmuraskin/Projects/CCD/working_v1/feedback_run-%d/feedback/_subject_id_%s/modelestimate/mapflow/_modelestimate0/results/%s%d.nii.gz' % (fbLoc,subj,t,i)
                        x.append(fname)
                    subjs = len(x)
                    merger = Merge()
                    merger.inputs.in_files = x
                    merger.inputs.dimension = 't'
                    merger.inputs.output_type = 'NIFTI_GZ'
                    merger.run()
                flameo = fsl.FLAMEO(cope_file='./cope'+str(i)+'_merged.nii.gz',var_cope_file='./varcope'+str(i)+'_merged.nii.gz',cov_split_file='design.grp',mask_file='/usr/share/fsl/5.0/data/standard/MNI152_T1_3mm_brain_mask.nii.gz',design_file='design.mat',t_con_file='design.con', run_mode='flame1')
                flameo.run()
                foldername='/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/flame/' + secondlevel_folder_names[fb] + '/cope' + str(i)
                if os.path.exists(foldername):
                    shutil.rmtree(foldername)
                    os.mkdir(foldername)
                else:
                    os.mkdir(foldername)
                shutil.move('cope' + str(i) + '_merged.nii.gz',foldername)
                shutil.move('varcope' + str(i) + '_merged.nii.gz',foldername)
                shutil.move('stats',foldername + '/stats')


    if runPair:
        pairedmodel = MultipleRegressDesign()
        pairedmodel.inputs.contrasts = [['A>B', 'T',['reg1'],[1]],['B>A', 'T',['reg1'],[-1]]]
        #make paired ttest model
        modelX=[0]*2*len(CCD_numbers)
        modelXAB=modelX
        modelXAB[0:len(CCD_numbers)]=[1]*len(CCD_numbers)
        modelDict=dict(reg1=modelXAB)
        for indx,subj in enumerate(CCD_numbers):
            modeltmp=[0]*2*len(CCD_numbers)
            modeltmp[indx]=1
            modeltmp[indx+len(CCD_numbers)]=1
            modelDict['s%d' % indx]= modeltmp
        pairedmodel.inputs.regressors = modelDict
        pairedmodel.run()



        for i in range(1,6):
            for t in ['cope', 'varcope']:
                x=['/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/flame/Feedback/cope' + str(i) + '/' + t + str(i) + '_merged.nii.gz',\
                '/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/flame/noFeedback/cope' + str(i) + '/' +t + str(i) + '_merged.nii.gz']
                merger = Merge()
                merger.inputs.in_files = x
                merger.inputs.dimension = 't'
                merger.inputs.output_type = 'NIFTI_GZ'
                merger.inputs.merged_file='./' + t + str(i)+'_merged.nii.gz'
                merger.run()

            flameo = fsl.FLAMEO(cope_file='./cope'+str(i)+'_merged.nii.gz',var_cope_file='./varcope'+str(i)+'_merged.nii.gz',cov_split_file='design.grp',mask_file='/usr/share/fsl/5.0/data/standard/MNI152_T1_3mm_brain_mask.nii.gz',design_file='design.mat',t_con_file='design.con', run_mode='flame1')
            flameo.run()
            foldername='/home/jmuraskin/Projects/CCD/working_v1/groupAnalysis/flame/paired-Ttest/cope' + str(i)
            if os.path.exists(foldername):
                shutil.rmtree(foldername)
                os.mkdir(foldername)
            else:
                os.mkdir(foldername)
            shutil.move('cope' + str(i) + '_merged.nii.gz',foldername)
            shutil.move('varcope' + str(i) + '_merged.nii.gz',foldername)
            shutil.move('stats',foldername)
