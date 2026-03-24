import type { Dispatch, SetStateAction } from 'react';
import ConsultationPage from '../../Consultation';
import CommunityPage from '../../Community';
import { type UseBoneAgeHistoryReturn } from '../hooks/useBoneAgeHistory';
import { type UsePredictionWorkspaceReturn } from '../hooks/usePredictionWorkspace';
import { type UserDashboardTab } from '../tabsConfig';
import type { PredictionResult } from '../types';
import FormulaMethodTab from './FormulaMethodTab';
import HistoryTab from './HistoryTab';
import ImagePreprocessingTab from './ImagePreprocessingTab';
import JointGradeTab from './JointGradeTab';
import ManualGradeTab from './ManualGradeTab';
import PredictTab from './PredictTab';
import SettingsTab from './SettingsTab';
import styles from '../UserDashboard.module.css';

interface UserDashboardContentProps {
  activeTab: UserDashboardTab;
  username: string | null;
  setActiveTab: (tab: UserDashboardTab) => void;
  jointResult: PredictionResult | null;
  setJointResult: Dispatch<SetStateAction<PredictionResult | null>>;
  predictionWorkspace: UsePredictionWorkspaceReturn;
  boneAgeHistory: UseBoneAgeHistoryReturn;
}

export default function UserDashboardContent({
  activeTab,
  username,
  setActiveTab,
  jointResult,
  setJointResult,
  predictionWorkspace,
  boneAgeHistory,
}: UserDashboardContentProps) {
  if (activeTab === 'predict') {
    return (
      <PredictTab
        file={predictionWorkspace.file}
        preview={predictionWorkspace.preview}
        imageStyle={predictionWorkspace.imageStyle}
        imgSettings={predictionWorkspace.imgSettings}
        setImgSettings={predictionWorkspace.setImgSettings}
        handleDrop={predictionWorkspace.handleDrop}
        fileInputRef={predictionWorkspace.fileInputRef}
        handleFileChange={predictionWorkspace.handleFileChange}
        result={predictionWorkspace.result}
        loading={predictionWorkspace.loading}
        gender={predictionWorkspace.gender}
        setGender={predictionWorkspace.setGender}
        realAge={predictionWorkspace.realAge}
        setRealAge={predictionWorkspace.setRealAge}
        currentHeight={predictionWorkspace.currentHeight}
        setCurrentHeight={predictionWorkspace.setCurrentHeight}
        handleSubmit={() => void predictionWorkspace.handleSubmit()}
        error={predictionWorkspace.error}
        generateComparisonData={predictionWorkspace.generateComparisonData}
        getEvaluation={predictionWorkspace.getEvaluation}
        getBoxStyle={predictionWorkspace.getBoxStyle}
        generateMedicalReport={predictionWorkspace.generateMedicalReport}
        imageSource={predictionWorkspace.predictionImageSource}
      />
    );
  }

  if (activeTab === 'history') {
    return (
      <HistoryTab
        pointTime={boneAgeHistory.pointTime}
        setPointTime={boneAgeHistory.setPointTime}
        pointBoneAge={boneAgeHistory.pointBoneAge}
        setPointBoneAge={boneAgeHistory.setPointBoneAge}
        pointChronAge={boneAgeHistory.pointChronAge}
        setPointChronAge={boneAgeHistory.setPointChronAge}
        pointNote={boneAgeHistory.pointNote}
        setPointNote={boneAgeHistory.setPointNote}
        addPoint={boneAgeHistory.addPoint}
        pointLoading={boneAgeHistory.pointLoading}
        trendData={boneAgeHistory.trendData}
        trend={boneAgeHistory.trend}
        boneAgePoints={boneAgeHistory.boneAgePoints}
        history={boneAgeHistory.history}
        restoreHistoryItem={predictionWorkspace.restoreHistoryItem}
        setActiveTab={setActiveTab}
        openUpdatePrediction={boneAgeHistory.openUpdatePrediction}
        historyMessage={boneAgeHistory.historyMessage}
        editingPrediction={boneAgeHistory.editingPrediction}
        editingPredictionValue={boneAgeHistory.editingPredictionValue}
        setEditingPredictionValue={boneAgeHistory.setEditingPredictionValue}
        confirmUpdatePrediction={boneAgeHistory.confirmUpdatePrediction}
        cancelUpdatePrediction={boneAgeHistory.cancelUpdatePrediction}
        openDeletePoint={boneAgeHistory.openDeletePoint}
        pendingDeletePointId={boneAgeHistory.pendingDeletePointId}
        confirmDeletePoint={boneAgeHistory.confirmDeletePoint}
        cancelDeletePoint={boneAgeHistory.cancelDeletePoint}
      />
    );
  }

  if (activeTab === 'joint-grade') {
    return (
      <div className={styles.jointContainer}>
        <div className={styles.resultsCard}>
          <h3 style={{ marginBottom: '1.2rem' }}>小关节成熟度分级</h3>
          <JointGradeTab result={jointResult} setResult={setJointResult} />
        </div>
      </div>
    );
  }

  if (activeTab === 'formula') {
    return (
      <div className={styles.jointContainer}>
        <div className={styles.resultsCard}>
          <h3 style={{ marginBottom: '1.2rem' }}>公式法预测骨龄</h3>
          <FormulaMethodTab result={jointResult} setResult={setJointResult} />
        </div>
      </div>
    );
  }

  if (activeTab === 'manual-grade') {
    return (
      <div className={styles.jointContainer}>
        <ManualGradeTab result={jointResult} />
      </div>
    );
  }

  if (activeTab === 'consultation') {
    return <ConsultationPage />;
  }

  if (activeTab === 'community') {
    return <CommunityPage />;
  }

  if (activeTab === 'preprocessing') {
    return (
      <ImagePreprocessingTab
        seedImage={predictionWorkspace.preprocessingSeedImage}
        onUseInPredict={(payload) => {
          predictionWorkspace.handleUsePreprocessedImage(payload);
          setActiveTab('predict');
        }}
      />
    );
  }

  return <SettingsTab username={username} onUpdateSuccess={() => undefined} />;
}
