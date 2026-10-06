'use client';

import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { signIn } from '@/lib/auth';
import { Button } from '@/components/ui/AppButton';
import { Input } from '@/components/ui/AppInput';
import { Loader2, Mail, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters long'),
});

interface MobileLoginFormProps {
  onSuccess?: () => void;
  isLoading?: boolean;
}

export default function MobileLoginForm({
  onSuccess,
  isLoading = false
}: MobileLoginFormProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isValid, isDirty },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const emailValue = useWatch({ control, name: 'email' });
  const passwordValue = useWatch({ control, name: 'password' });

  const onSubmit = async (data: z.infer<typeof loginSchema>) => {
    setError(null);

    try {
      const result = await signIn.email({
        email: data.email,
        password: data.password,
        callbackURL: '/dashboard',
      });

      if (result.error) {
        setError(result.error.message || 'Login failed');
      } else {
        // Handle remember me
        if (rememberMe) {
          localStorage.setItem('remember_me', 'true');
        } else {
          localStorage.removeItem('remember_me');
        }

        onSuccess?.();
      }
    } catch (err) {
      console.error('Login error:', err);
      const errorMessage = err instanceof Error && err.message ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      {/* Email Input with Icon */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none z-10">
          <Mail className="h-5 w-5 text-gray-400" />
        </div>
        <Input
          id="mobile-email"
          type="email"
          placeholder="Email address"
          error={errors.email?.message}
          {...register('email')}
          autoComplete="email"
          autoFocus
          className="pl-10"
          aria-describedby={errors.email ? "mobile-email-error" : undefined}
        />
        {emailValue && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <svg
              className={`h-4 w-4 ${/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue) ? 'text-green-500' : 'text-gray-400'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        )}
      </div>

      {/* Password Input with Icon */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none z-10">
          <Lock className="h-5 w-5 text-gray-400" />
        </div>
        <Input
          id="mobile-password"
          type={showPassword ? "text" : "password"}
          placeholder="Password"
          error={errors.password?.message}
          {...register('password')}
          autoComplete="current-password"
          className="pl-10 pr-10"
          aria-describedby={errors.password ? "mobile-password-error" : undefined}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute inset-y-0 right-0 pr-3 flex items-center"
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? (
            <EyeOff className="h-5 w-5 text-gray-400" />
          ) : (
            <Eye className="h-5 w-5 text-gray-400" />
          )}
        </button>
      </div>

      {/* Remember Me & Forgot Password */}
      <div className="flex items-center justify-between">
        <label className="flex items-center text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <span>Remember me</span>
        </label>

        <a
          href="/auth/forgot-password"
          className="text-sm text-blue-600 hover:text-blue-500"
          aria-label="Forgot password?"
        >
          Forgot password?
        </a>
      </div>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-red-50 border border-red-200 rounded-lg p-3"
            role="alert"
            aria-live="assertive"
          >
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit Button */}
      <Button
        type="submit"
        className={`w-full py-3 text-base font-medium ${
          isValid && isDirty
            ? 'bg-gradient-to-r from-blue-600 to-indigo-700 text-white hover:from-blue-700 hover:to-indigo-800'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
        loading={isLoading}
        disabled={isLoading || !isValid || !isDirty}
        aria-label="Sign in"
      >
        {isLoading ? (
          <div className="flex items-center justify-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Signing in...</span>
          </div>
        ) : (
          <span>Sign In</span>
        )}
      </Button>

      {/* Password strength indicator */}
      {passwordValue?.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  passwordValue.length >= 6
                    ? passwordValue.length >= 10
                      ? 'bg-green-500'
                      : 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(passwordValue.length * 10, 100)}%` }}
              />
            </div>
            <span
              className={`text-xs font-medium ${
                passwordValue.length >= 6
                  ? passwordValue.length >= 10
                    ? 'text-green-600'
                    : 'text-yellow-600'
                  : 'text-red-600'
              }`}
            >
              {passwordValue.length >= 6
                ? passwordValue.length >= 10
                  ? 'Strong'
                  : 'Medium'
                : 'Weak'
              }
            </span>
          </div>
          <p className="text-xs text-gray-500">
            Password must be at least 6 characters long
          </p>
        </div>
      )}

      {/* Security Notice */}
      <div className="text-center">
        <p className="text-xs text-gray-500">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>

      {/* Keyboard Shortcuts */}
      <details className="text-sm text-gray-600">
        <summary className="cursor-pointer hover:text-gray-800">
          Keyboard shortcuts
        </summary>
        <div className="mt-2 space-y-1 text-xs">
          <p><kbd className="px-2 py-1 bg-gray-100 rounded">Enter</kbd> - Submit form</p>
          <p><kbd className="px-2 py-1 bg-gray-100 rounded">Tab</kbd> - Navigate fields</p>
          <p><kbd className="px-2 py-1 bg-gray-100 rounded">Esc</kbd> - Clear form</p>
        </div>
      </details>
    </form>
  );
}