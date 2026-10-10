import React from 'react';
import { useUIStore } from '@/stores/useUIStore';
import { LandingHero } from '@/components/landing/LandingHero';
import { WorkspaceShell } from '@/components/layout/WorkspaceShell';

export const App: React.FC = () => {
  const { currentScreen } = useUIStore();
  const isHero = currentScreen === 'landing';

  return (
    <div id="app" className={`view-viewport app-root ${isHero ? 'hero-active' : 'workspace-active'}`}>
      <div className="view-screen">
        {isHero ? <LandingHero /> : <WorkspaceShell />}
      </div>
    </div>
  );
};
