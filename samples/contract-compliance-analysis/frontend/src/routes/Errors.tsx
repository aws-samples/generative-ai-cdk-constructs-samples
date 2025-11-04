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

import { useRouteError, isRouteErrorResponse, Link } from "react-router";
import { AlertCircle, BugIcon, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import HeaderGradient from "@/components/HeaderGradient";
import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

function errorMessage(error: unknown): string {
  if (isRouteErrorResponse(error)) {
    return `${error.status} - ${error.statusText}`;
  } else if (error instanceof Error) {
    return error.message;
  } else if (typeof error === "string") {
    return error;
  } else if (error && typeof error === "object" && "message" in error) {
    // Handle case where error is an object with a message property
    return String((error as { message: string }).message);
  } else {
    console.error("Unknown error: %d", error);
    return "Unknown error";
  }
}

export function Errors() {
  const routeError = useRouteError();
  const error = errorMessage(routeError);
  const { t } = useTranslation();

  return (
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center p-4">
      <HeaderGradient
        animate={true}
        lightColors={["#ff6b6b", "#f06595", "#ff5da8", "#ff6b6b"]}
        darkColors={["#ff6b6b", "#f06595", "#ff5da8", "#ff6b6b"]}
        lightOpacity={100}
        darkOpacity={50}
        animationDuration={30}
        className="bg-red-50"
        maskClassName="fill-red-50"
      />

      <div className="z-10 w-full max-w-xl overflow-hidden rounded-xl bg-white shadow-lg dark:bg-neutral-900">
        <div className="flex flex-col items-center p-8 text-center">
          <div className="mb-4 rounded-full bg-red-100 p-3 dark:bg-red-900/30">
            <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
          </div>

          <h2 className="mb-2 text-2xl font-bold text-neutral-900 dark:text-neutral-100">
            {t("errors.title")}
          </h2>

          <p className="mb-4 text-neutral-600 dark:text-neutral-300">
            {t("errors.message")}
          </p>

          <div className="mb-4 w-full text-left">
            <p className="mb-2 text-sm font-medium text-neutral-500 dark:text-neutral-400">
              Error:{" "}
              <span className="rounded-sm p-1 font-mono text-red-600 dark:bg-red-950 dark:text-red-400">
                {error.split(" - ")[0]}
              </span>
            </p>

            <Accordion type="single" collapsible className="mt-4 w-full">
              <AccordionItem value="error-details" className="border-b-0">
                <AccordionTrigger className="mb-2 cursor-pointer rounded bg-neutral-100 p-2 py-2 text-xs font-medium text-neutral-700 dark:bg-foreground dark:text-neutral-300">
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <BugIcon size={16} /> {t("errors.errorObject")}
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="w-full overflow-auto rounded-md bg-neutral-100 p-4 dark:bg-neutral-800">
                    <code className="whitespace-pre-wrap break-all text-xs text-red-600 dark:text-red-400">
                      {JSON.stringify(routeError, null, 2)}
                    </code>
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>

          <Button variant={"secondary"} asChild className="mb-4">
            <Link to="/">
              <Home className="mr-2 h-4 w-4" />
              {t("errors.backHome")}
            </Link>
          </Button>
        </div>

        <div
          className={cn(
            "border-t border-neutral-200 dark:border-neutral-800",
            "px-8 py-4 text-center font-mono text-xs text-neutral-400 dark:text-neutral-200",
          )}
        >
          {t("errors.built")}
        </div>
      </div>
    </div>
  );
}
