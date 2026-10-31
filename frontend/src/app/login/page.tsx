import { redirect } from 'next/navigation';

import LoginForm from '@/components/auth/login-form';
import { getSessionUser } from '@/lib/auth/session';

export default async function LoginPage() {
  const user = await getSessionUser();
  if (user) {
    redirect('/');
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4 py-8">
      <LoginForm />
    </div>
  );
}
