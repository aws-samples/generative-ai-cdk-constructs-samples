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

import { useCallback, useRef } from 'react';

export interface FormResetOptions {
  resetOnSuccess?: boolean;
  resetOnCancel?: boolean;
  confirmReset?: boolean;
}

export function useFormReset<T>(
  initialData: T,
  setFormData: (data: T) => void,
  setErrors?: (errors: Record<string, string>) => void,
  options: FormResetOptions = {}
) {
  const { resetOnSuccess = false, resetOnCancel = true, confirmReset = false } = options;
  const hasChangesRef = useRef(false);

  const resetForm = useCallback((force: boolean = false) => {
    if (!force && confirmReset && hasChangesRef.current) {
      const confirmed = window.confirm(
        'Are you sure you want to reset the form? All unsaved changes will be lost.'
      );
      if (!confirmed) return false;
    }

    setFormData(initialData);
    setErrors?.({});
    hasChangesRef.current = false;
    return true;
  }, [initialData, setFormData, setErrors, confirmReset]);

  const markAsChanged = useCallback(() => {
    hasChangesRef.current = true;
  }, []);

  const handleSuccess = useCallback(() => {
    if (resetOnSuccess) {
      resetForm(true);
    }
  }, [resetOnSuccess, resetForm]);

  const handleCancel = useCallback(() => {
    if (resetOnCancel) {
      return resetForm();
    }
    return true;
  }, [resetOnCancel, resetForm]);

  return {
    resetForm,
    markAsChanged,
    handleSuccess,
    handleCancel,
    hasChanges: hasChangesRef.current,
  };
}