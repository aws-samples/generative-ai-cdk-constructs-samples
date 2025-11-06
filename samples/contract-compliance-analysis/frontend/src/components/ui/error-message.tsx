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

import { AlertCircleIcon, XCircleIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface ErrorMessageProps {
  message: string;
  variant?: 'inline' | 'banner';
  className?: string;
}

export function ErrorMessage({ message, variant = 'inline', className }: ErrorMessageProps) {
  if (variant === 'banner') {
    return (
      <div className={cn(
        "flex items-center gap-2 p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md",
        className
      )}>
        <XCircleIcon className="h-4 w-4 flex-shrink-0" />
        <span>{message}</span>
      </div>
    );
  }

  return (
    <div className={cn(
      "flex items-center gap-1 text-sm text-red-600",
      className
    )}>
      <AlertCircleIcon className="h-4 w-4 flex-shrink-0" />
      <span>{message}</span>
    </div>
  );
}

interface FieldErrorProps {
  error?: string;
  className?: string;
}

export function FieldError({ error, className }: FieldErrorProps) {
  if (!error) return null;

  return <ErrorMessage message={error} variant="inline" className={className} />;
}

interface ErrorBannerProps {
  error?: string | null;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorBanner({ error, onDismiss, className }: ErrorBannerProps) {
  if (!error) return null;

  return (
    <div className={cn(
      "flex items-center justify-between p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md",
      className
    )}>
      <div className="flex items-center gap-2">
        <XCircleIcon className="h-4 w-4 flex-shrink-0" />
        <span>{error}</span>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-red-500 hover:text-red-700 transition-colors"
          aria-label="Dismiss error"
        >
          <XCircleIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}