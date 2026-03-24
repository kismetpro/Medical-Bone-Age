import SharedSettingsTab from '../../../components/settings/SharedSettingsTab';

interface SettingsTabProps {
  username: string | null;
  onUpdateSuccess?: () => void;
}

export default function SettingsTab({ username, onUpdateSuccess }: SettingsTabProps) {
  return <SharedSettingsTab username={username} mode="user" onUpdateSuccess={onUpdateSuccess} />;
}
