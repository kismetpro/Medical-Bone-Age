import SharedSettingsTab from '../../../components/settings/SharedSettingsTab';

interface DoctorSettingsTabProps {
  username: string | null;
  isSuperAdmin: boolean;
  onUpdateSuccess?: () => void;
}

export default function DoctorSettingsTab({
  username,
  isSuperAdmin,
  onUpdateSuccess,
}: DoctorSettingsTabProps) {
  return (
    <SharedSettingsTab
      username={username}
      mode="doctor"
      isSuperAdmin={isSuperAdmin}
      onUpdateSuccess={onUpdateSuccess}
    />
  );
}
