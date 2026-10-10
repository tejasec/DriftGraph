import React from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { LandingHero } from '@/components/landing/LandingHero';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';

export const App: React.FC = () => {
  const { currentScreen } = useUIStore();

  return (
    <div className="w-screen h-screen overflow-hidden">
      {currentScreen === 'landing' ? <LandingHero /> : <WorkspaceShell />}
    </div>
  );
};
