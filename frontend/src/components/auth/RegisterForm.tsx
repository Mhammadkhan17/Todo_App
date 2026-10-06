'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '../ui/AppButton';
import { Input } from '../ui/AppInput';

const registerSchema = z
  .object({
    email: z.string().email('Invalid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(8, 'Password confirmation must be at least 8 characters'),
    username: z.string().min(3, 'Username must be at least 3 characters'),
    full_name: z.string().optional(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ['confirm_password'],
  });

interface RegisterFormProps {
  onSuccess?: () => void;
}

export default function RegisterForm({ onSuccess }: RegisterFormProps) {
  const { register: registerUser } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      password: '',
      confirm_password: '',
      username: '',
      full_name: '',
    },
  });

  const onSubmit = async (data: z.infer<typeof registerSchema>) => {
    setIsLoading(true);
    setError(null);

    try {
      await registerUser(data.email, data.password, data.username, data.full_name);

      // Registration successful, trigger success callback
      onSuccess?.();
    } catch (err) {
      console.error('Registration error:', err);
      setError(err instanceof Error && err.message ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <Input
        id="email"
        type="email"
        label="Security Email"
        placeholder="user@protocol.io"
        error={errors.email?.message}
        {...register('email')}
      />

      <Input
        id="username"
        type="text"
        label="Handle"
        placeholder="identity_01"
        error={errors.username?.message}
        {...register('username')}
      />

      <Input
        id="full_name"
        type="text"
        label="Legal Name"
        placeholder="Optional"
        error={errors.full_name?.message}
        {...register('full_name')}
      />

      <Input
        id="password"
        type="password"
        label="Access Key"
        placeholder="••••••••"
        error={errors.password?.message}
        {...register('password')}
      />

      <Input
        id="confirm_password"
        type="password"
        label="Confirm Access Key"
        placeholder="••••••••"
        error={errors.confirm_password?.message}
        {...register('confirm_password')}
      />

      {error && (
        <div role="alert" aria-live="assertive" className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-[4px] text-xs font-mono uppercase tracking-widest">
          {error}
        </div>
      )}

      <div className="pt-2">
        <Button
          type="submit"
          className="w-full bg-emerald-600 hover:bg-emerald-500 text-[#0a0a0a] font-bold border-none rounded-[4px] py-6 shadow-[0_0_30px_rgba(16,185,129,0.2)]"
          loading={isLoading}
          disabled={isLoading}
        >
          Initialize Account
        </Button>
      </div>
    </form>
  );
}