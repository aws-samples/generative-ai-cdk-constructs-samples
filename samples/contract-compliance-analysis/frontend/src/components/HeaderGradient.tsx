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

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface HeaderGradientProps {
  /** Array of colors for light mode */
  lightColors?: string[];
  /** Array of colors for dark mode */
  darkColors?: string[];
  /** Light mode opacity (0-100) */
  lightOpacity?: number;
  /** Dark mode opacity (0-100) */
  darkOpacity?: number;
  /** Animation duration in seconds */
  animationDuration?: number;
  /** Whether to animate the gradient */
  animate?: boolean;
  /** Gradient angle (e.g. "90deg", "135deg") */
  angle?: string;
  /** Background size scale (number or "auto") */
  gradientScale?: number | "auto";
  /** Additional classes */
  className?: string;
  /** Additional classes for the mask */
  maskClassName?: string;
}

export default function HeaderGradient({
  lightColors = ["#feb303", "#8e07ef", "#feb303"],
  darkColors = ["#36b49f", "#DBFF75", "#36b49f"],
  lightOpacity = 40,
  darkOpacity = 100,
  animationDuration = 12,
  animate = false,
  angle = "90deg",
  gradientScale = "auto",
  className,
  maskClassName,
}: HeaderGradientProps) {
  const styleRef = useRef<HTMLStyleElement>(null);

  // Calculate gradient scale
  const getScale = (colors: string[]): number => {
    if (gradientScale !== "auto") return gradientScale;
    return Math.max(colors.length * 80, 200);
  };

  const lightScale = getScale(lightColors);
  const darkScale = getScale(darkColors);

  useEffect(() => {
    if (!styleRef.current) return;

    if (animate) {
      const lightGradientStr = createGradientString(lightColors, angle);
      const darkGradientStr = createGradientString(darkColors, angle);

      styleRef.current.textContent = `
        @keyframes slideGradient {
          0% {
            background-position: 0% 50%;
          }
          100% {
            background-position: ${lightScale}% 50%;
          }
        }

        .gradient-light.animate {
          background: ${lightGradientStr};
          background-size: ${lightScale}% ${lightScale}%;
          animation: slideGradient ${animationDuration}s ease infinite;
        }

        @keyframes slideDarkGradient {
          0% {
            background-position: 0% 50%;
          }
          100% {
            background-position: ${darkScale}% 50%;
          }
        }

        .dark .gradient-dark.animate {
          background: ${darkGradientStr} !important;
          background-size: ${darkScale}% ${darkScale}% !important;
          animation: slideDarkGradient ${animationDuration}s ease infinite !important;
        }
      `;
    } else {
      styleRef.current.textContent = "";
    }
  }, [
    lightColors,
    darkColors,
    animationDuration,
    animate,
    angle,
    lightScale,
    darkScale,
  ]);

  const createGradientString = (colors: string[], gradientAngle: string) => {
    const loopableColors = [...colors];
    if (loopableColors[0] !== loopableColors[loopableColors.length - 1]) {
      loopableColors.push(loopableColors[0]);
    }
    return `linear-gradient(${gradientAngle}, ${loopableColors.join(", ")})`;
  };

  return (
    <div
      className={cn(
        "absolute inset-0 -z-10 mx-0 max-w-none overflow-hidden",
        className,
      )}
    >
      <div className="absolute left-1/2 top-0 ml-[-38rem] h-[25rem] w-[81.25rem] dark:[mask-image:linear-gradient(white,transparent)]">
        <div
          className={cn(
            "gradient-light gradient-dark absolute inset-0",
            "[mask-image:radial-gradient(farthest-side_at_top,white,transparent)]",
            { animate: animate },
          )}
          style={{
            background: animate
              ? undefined
              : createGradientString(lightColors, angle),
            backgroundSize: animate
              ? undefined
              : `${lightScale}% ${lightScale}%`,
            opacity: lightOpacity / 100,
          }}
        ></div>
        <svg
          viewBox="0 0 1113 440"
          aria-hidden="true"
          className={cn(
            "absolute left-1/2 top-0 ml-[-19rem] w-[69.5625rem] fill-background blur-[30px] dark:hidden",
            maskClassName,
          )}
        >
          <path d="M.016 439.5s-9.5-300 434-300S882.516 20 882.516 20V0h230.004v439.5H.016Z"></path>
        </svg>

        {/* Animation styles */}
        <style ref={styleRef}></style>

        {/* Base styles */}
        <style>
          {`
            .gradient-light, .gradient-dark {
              will-change: background-position;
            }

            .dark .gradient-dark {
              background: ${createGradientString(darkColors, angle)} !important;
              background-size: ${darkScale}% ${darkScale}% !important;
              opacity: ${darkOpacity / 100} !important;
            }
          `}
        </style>
      </div>
    </div>
  );
}
