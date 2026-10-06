'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSession } from '@/lib/auth';
import MobileLoginForm from '@/components/auth/MobileLoginForm';
import { Loader2, CheckCircle } from 'lucide-react';
import AnimatedBackground from '@/components/auth/AnimatedBackground';

export default function MobileLoginPage() {
  const router = useRouter();
  const { data, isPending } = useSession();
  const session = data;
  const loading = isPending;
  const [showSuccess, setShowSuccess] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (session && !loading) {
      router.push('/dashboard');
    }
  }, [session, loading, router]);

  const handleLoginSuccess = () => {
    setShowSuccess(true);
    // Redirect after a brief delay to show the welcome message
    setTimeout(() => {
      router.push('/dashboard');
    }, 1500); // Wait 1.5 seconds before redirecting
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900">
      {/* Mobile-specific background */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Subtle animated elements */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:60px_60px]"></div>

        {/* Floating particles */}
        <div className="absolute inset-0">
          <AnimatedBackground particleCount={15} />
        </div>
      </div>

      {/* Main content */}
      <div className="relative z-10 min-h-screen flex flex-col px-4 py-6">
        {/* Mobile header */}
        <header className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h1 className="text-xl font-bold text-white">TodoFlow</h1>
              </div>
            </motion.div>

            <nav className="flex items-center gap-4">
              <Link href="/" className="text-white/70 hover:text-white transition-colors text-sm">Home</Link>
              <Link href="/auth/register" className="text-white/70 hover:text-white transition-colors text-sm">Sign Up</Link>
            </nav>
          </div>
        </header>

        {/* Main content area */}
        <main className="flex-1 flex items-center justify-center">
          <div className="w-full max-w-sm">
            <AnimatePresence mode="wait">
              {!loading && !session && !showSuccess && (
                <motion.div
                  key="login-form"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.3 }}
                  className="bg-white/10 backdrop-blur-2xl border border-white/20 rounded-2xl shadow-xl p-6"
                >
                  <div className="text-center mb-6">
                    <h2 className="text-2xl font-bold text-white mb-2">Welcome Back</h2>
                    <p className="text-white/70 text-sm">Sign in to continue</p>
                  </div>

                  <MobileLoginForm
                    onSuccess={handleLoginSuccess}
                  />
                </motion.div>
              )}

              {/* Success state */}
              {showSuccess && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-2xl border border-green-500/30 rounded-2xl shadow-xl p-8 text-center"
                >
                  <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
                  <h3 className="text-2xl font-bold text-white mb-2">Welcome back!</h3>
                  <p className="text-white/70 mb-6">Redirecting to your dashboard...</p>
                  <div className="flex justify-center">
                    <Loader2 className="w-6 h-6 text-green-400 animate-spin" />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </main>

        {/* Mobile footer */}
        <footer className="mt-8 text-center">
          <p className="text-xs text-white/50">
            © 2024 TodoFlow. All rights reserved.
          </p>
        </footer>
      </div>

      {/* Mobile navigation hints */}
      <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 z-20">
        <div className="bg-black/50 backdrop-blur-md rounded-full px-4 py-2">
          <p className="text-xs text-white/70">
            Swipe up to continue
          </p>
        </div>
      </div>
    </div>
  );
}