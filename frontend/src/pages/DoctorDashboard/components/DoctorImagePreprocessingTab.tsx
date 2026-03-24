import ImagePreprocessingWorkspace from '../../../components/image-preprocessing/ImagePreprocessingWorkspace';

export default function DoctorImagePreprocessingTab() {
  return (
    <ImagePreprocessingWorkspace
      title="医学图像预处理"
      uploadLabel="选择医学图像"
      enhancementTitle="医学图像增强"
      placeholderTitle="请上传医学图像开始处理"
      placeholderHint="支持 X 光片、CT、MRI 等常见医学图像格式。"
      downloadLabel="下载处理图像"
      showEdgeEnhance
      showBrightnessInfo
    />
  );
}
