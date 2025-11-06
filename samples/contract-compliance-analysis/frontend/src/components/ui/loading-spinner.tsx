//
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
// with the License. A copy of the License is located at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
// OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
// and limitations under the License.
//

import { Loader2Icon } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
};

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  return (
    <Loader2Icon
      className={cn(
        'animate-spin',
        sizeClasses[size],
        className
      )}
    />
  );
}

interface LoadingStateProps {
  loading: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  className?: string;
}

export function LoadingState({ loading, children, fallback, className }: LoadingStateProps) {
  if (loading) {
    return (
      <div className={cn('flex items-center justify-center p-4', className)}>
        {fallback || <LoadingSpinner />}
      </div>
    );
  }

  return <>{children}</>;
}

interface InlineLoadingProps {
  loading: boolean;
  text?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function InlineLoading({ loading, text, size = 'sm', className }: InlineLoadingProps) {
  if (!loading) return null;

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <LoadingSpinner size={size} />
      {text && <span className="text-sm text-muted-foreground">{text}</span>}
    </div>
  );
}

interface ButtonLoadingProps {
  loading: boolean;
  children: React.ReactNode;
  loadingText?: string;
}

export function ButtonLoading({ loading, children, loadingText }: ButtonLoadingProps) {
  if (loading) {
    return (
      <>
        <LoadingSpinner size="sm" className="mr-2" />
        {loadingText || children}
      </>
    );
  }

  return <>{children}</>;
}