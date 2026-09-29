import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './app/App';
import { ModuleApi } from './features/modules/services/ModuleApi';
import { SessionApi } from './features/sessions/services/SessionApi';
import { SubmissionApi } from './features/submissions/services/SubmissionApi';
import './styles.css';

const api = new ModuleApi('/api', fetch);
const sessionApi = new SessionApi('/api', fetch);
const submissionApi = new SubmissionApi('/api', fetch);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App api={api} sessionApi={sessionApi} submissionApi={submissionApi} /></React.StrictMode>,
);
