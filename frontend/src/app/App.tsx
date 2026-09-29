import { useEffect } from 'react';
import { JuniorPage } from '../pages/junior/JuniorPage';
import { JuniorProfilePage } from '../pages/junior/JuniorProfilePage';
import { SeniorPage } from '../pages/senior/SeniorPage';
import type { ModuleApi } from '../features/modules/services/ModuleApi';
import type { SessionApi } from '../features/sessions/services/SessionApi';
import type { SubmissionApi } from '../features/submissions/services/SubmissionApi';

type AppProps = { api: ModuleApi; sessionApi: SessionApi; submissionApi: SubmissionApi };

export function App({ api, sessionApi, submissionApi }: AppProps) {
  useEffect(() => {
    if (!['/senior', '/junior', '/junior/profile'].includes(window.location.pathname)) {
      window.history.replaceState(null, '', `/senior${window.location.search}${window.location.hash}`);
    }
  }, []);

  if (window.location.pathname === '/junior/profile') return <JuniorProfilePage />;

  return window.location.pathname === '/junior'
    ? <JuniorPage api={api} sessionApi={sessionApi} submissionApi={submissionApi} />
    : <SeniorPage api={api} />;
}
