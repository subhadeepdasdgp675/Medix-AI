import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Dashboard } from './pages/Dashboard';
import { NewPatientCase } from './pages/NewPatientCase';
import { DrugInteraction } from './pages/DrugInteraction';
import { ResistanceMap } from './pages/ResistanceMap';
import { PatientReport } from './pages/PatientReport';
import { Settings } from './pages/Settings';
import { Background3D } from './components/Background3D';
import './index.css';

function App() {
  return (
    <>
      <Background3D />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/new-case" element={<NewPatientCase />} />
          <Route path="/drug-interaction" element={<DrugInteraction />} />
          <Route path="/resistance-map" element={<ResistanceMap />} />
          <Route path="/reports" element={<PatientReport />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
    </>
  );
}

export default App;
