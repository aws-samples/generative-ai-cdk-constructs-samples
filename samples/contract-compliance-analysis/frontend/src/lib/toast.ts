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

import { toast } from 'sonner';

export interface ToastOptions {
  duration?: number;
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  dismissible?: boolean;
}

export const showToast = {
  success: (message: string, options?: ToastOptions) => {
    return toast.success(message, {
      duration: options?.duration || 4000,
      position: options?.position || 'top-right',
      dismissible: options?.dismissible !== false,
    });
  },

  error: (message: string, options?: ToastOptions) => {
    return toast.error(message, {
      duration: options?.duration || 6000,
      position: options?.position || 'top-right',
      dismissible: options?.dismissible !== false,
    });
  },

  warning: (message: string, options?: ToastOptions) => {
    return toast.warning(message, {
      duration: options?.duration || 5000,
      position: options?.position || 'top-right',
      dismissible: options?.dismissible !== false,
    });
  },

  info: (message: string, options?: ToastOptions) => {
    return toast.info(message, {
      duration: options?.duration || 4000,
      position: options?.position || 'top-right',
      dismissible: options?.dismissible !== false,
    });
  },

  loading: (message: string, options?: ToastOptions) => {
    return toast.loading(message, {
      duration: options?.duration || Infinity,
      position: options?.position || 'top-right',
      dismissible: options?.dismissible !== false,
    });
  },

  promise: <T>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: unknown) => string);
    }
  ) => {
    return toast.promise(promise, messages);
  },

  dismiss: (toastId?: string | number) => {
    return toast.dismiss(toastId);
  },
};

// Convenience functions for common guideline operations
export const guidelineToasts = {
  createSuccess: (name: string | undefined) =>
    showToast.success(`Guideline "${name || 'Unknown'}" created successfully`),

  updateSuccess: (name: string | undefined) =>
    showToast.success(`Guideline "${name || 'Unknown'}" updated successfully`),

  deleteSuccess: (name: string | undefined) =>
    showToast.success(`Guideline "${name || 'Unknown'}" deleted successfully`),

  createError: (error: string) =>
    showToast.error(`Failed to create guideline: ${error || 'Unknown error'}`),

  updateError: (error: string) =>
    showToast.error(`Failed to update guideline: ${error || 'Unknown error'}`),

  deleteError: (error: string) =>
    showToast.error(`Failed to delete guideline: ${error || 'Unknown error'}`),

  loadError: (error: string) =>
    showToast.error(`Failed to load guidelines: ${error || 'Unknown error'}`),
};