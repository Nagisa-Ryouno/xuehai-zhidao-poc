import type { AppRole, StudentSubRoute, TeacherSubRoute } from '../router';

export interface AppContextValue {
  role: AppRole;
  path: string;
  subRoute: StudentSubRoute | TeacherSubRoute;
  studentId: string;
  navigate: (newPath: string) => void;
  switchRole: (targetRole: AppRole) => void;
  selectStudent: (newStudentId: string) => void;
}
