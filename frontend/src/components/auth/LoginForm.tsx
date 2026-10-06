'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/AppButton';
import { Input } from '@/components/ui/AppInput';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters long'),
});

interface LoginFormProps {
  onSuccess?: () => void;
}

export default function LoginForm({ onSuccess }: LoginFormProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const { login } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isDirty },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = async (data: z.infer<typeof loginSchema>) => {
    setIsLoading(true);
    setError(null);

    try {
      await login(data.email, data.password);

      // Handle remember me
      if (rememberMe) {
        localStorage.setItem('remember_me', 'true');
      } else {
        localStorage.removeItem('remember_me');
      }

      onSuccess?.();
    } catch (err) {
      console.error('Login error:', err);
      const errorMessage = err instanceof Error && err.message ? err.message : 'Login failed';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <Input
        id="email"
        type="email"
        label="Identity (Email)"
        placeholder="user@protocol.io"
        error={errors.email?.message}
        {...register('email')}
        autoComplete="email"
        autoFocus
      />

      <Input
        id="password"
        type={showPassword ? "text" : "password"}
        label="Access Key"
        placeholder="••••••••"
        error={errors.password?.message}
        {...register('password')}
        autoComplete="current-password"
        showPasswordToggle
        onTogglePassword={() => setShowPassword(!showPassword)}
        passwordVisible={showPassword}
      />

      {/* Remember Me & Forgot Password */}
      <div className="flex items-center justify-between px-1">
        <label className="flex items-center text-[10px] font-mono uppercase tracking-widest text-stone-500 cursor-pointer hover:text-emerald-500 transition-colors">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="mr-3 h-3 w-3 bg-[#141414] border-stone-800 rounded-[2px] text-emerald-500 focus:ring-0"
          />
          Persist Session
        </label>

        <a
          href="/auth/forgot-password"
          className="text-[10px] font-mono uppercase tracking-widest text-stone-500 hover:text-emerald-500 transition-colors"
        >
          Recover Key
        </a>
      </div>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            role="alert"
            aria-live="assertive"
            className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-[4px] text-xs font-mono uppercase tracking-widest"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit Button */}
      <div className="pt-2">
        <Button
          type="submit"
          className={`w-full py-6 font-bold text-lg rounded-[4px] border-none transition-all duration-300 ${
            isValid && isDirty
              ? 'bg-emerald-600 hover:bg-emerald-500 text-[#0a0a0a] shadow-[0_0_30px_rgba(16,185,129,0.2)]'
              : 'bg-stone-800 text-stone-500 cursor-not-allowed'
          }`}
          loading={isLoading}
          disabled={isLoading || !isValid || !isDirty}
        >
          {isLoading ? 'Verifying...' : 'Initialize Session'}
        </Button>
      </div>
    </form>
  );
}