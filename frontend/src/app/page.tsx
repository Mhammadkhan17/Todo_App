'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useSession } from '@/lib/auth';
import { motion } from 'framer-motion';

export default function Home() {
  const router = useRouter();
  const { data: sessionData, isPending } = useSession();

  useEffect(() => {
    // Check authentication status first before redirecting
    if (!isPending) {
      if (sessionData && sessionData.user) {
        // User is authenticated, redirect to dashboard
        router.push('/dashboard');
      } else {
        // User is not authenticated, redirect to login
        router.push('/auth/login');
      }
    }
  }, [sessionData, isPending, router]);

  if (isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a] text-[#fafaf9] overflow-hidden relative">
        {/* Structural Grid Background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1c1917_1px,transparent_1px),linear-gradient(to_bottom,#1c1917_1px,transparent_1px)] bg-[size:40px_40px] opacity-[0.15]"></div>
        
        <main className="relative z-10 flex flex-col items-center max-w-xl w-full px-6">
          {/* Brand Identity */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-12 text-center"
          >
            <div className="w-16 h-16 mx-auto bg-emerald-500 rounded-[4px] flex items-center justify-center shadow-[0_0_40px_rgba(16,185,129,0.2)] mb-8">
              <span className="text-[#0a0a0a] text-3xl font-bold">✓</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tighter text-white uppercase mb-2">
              TodoFlow<span className="text-emerald-500">.</span>
            </h1>
            <p className="text-[10px] font-mono text-stone-500 uppercase tracking-[0.3em]">
              Task Execution Protocol v2.5.0
            </p>
          </motion.div>

          {/* Initialization UI */}
          <div className="w-full bg-[#0f0f0f] border border-stone-800 rounded-[4px] p-8 shadow-[0_20px_50px_rgba(0,0,0,0.5)]">
            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between border-b border-stone-800/50 pb-4">
                <span className="text-[10px] font-mono text-stone-500 uppercase tracking-widest">Initialization_Status</span>
                <span className="text-[10px] font-mono text-emerald-500 animate-pulse uppercase tracking-tighter">Running</span>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                  <span className="text-xs font-mono text-stone-400">CONNECTING_TO_DATABASE... OK</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                  <span className="text-xs font-mono text-stone-400">VERIFYING_ENCRYPTION... OK</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 bg-stone-700 rounded-full animate-pulse" />
                  <span className="text-xs font-mono text-stone-200">CHECKING_SESSION_IDENTITY...</span>
                </div>
              </div>

              <div className="h-1 bg-stone-900 rounded-full overflow-hidden mt-4">
                <motion.div 
                  className="h-full bg-emerald-500"
                  initial={{ width: 0 }}
                  animate={{ width: '70%' }}
                  transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
                />
              </div>
            </div>
          </div>

          {/* Footer Metadata */}
          <div className="mt-12 flex flex-col items-center gap-2">
            <p className="text-[9px] font-mono text-stone-600 uppercase tracking-widest">Systems Secure // AES-256</p>
            <p className="text-[9px] font-mono text-stone-700 uppercase tracking-widest">&copy; 2026 Kinetic Productivity Labs</p>
          </div>
        </main>
      </div>
    );
  }

  // If authentication has been checked but we're still on this page (shouldn't happen),
  // we return null to avoid hydration issues
  return null;
}
