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

import { Outlet } from "react-router-dom";
import NavBar from "@/components/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { useState } from "react";

export default function Root() {

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);

  return (
    <div className="flex h-screen">
      <Sidebar 
        isCollapsed={isSidebarCollapsed} 
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)} 
      />
      <div className="flex-1 flex flex-col">
      <NavBar />
      <main className="container mx-auto mt-4">
        <div className="absolute inset-0 -z-10 mx-0 max-w-none overflow-hidden">
          <div className="absolute left-1/2 top-0 ml-[-38rem] h-[25rem] w-[81.25rem] dark:[mask-image:linear-gradient(white,transparent)]">
            <div className="absolute inset-0 bg-gradient-to-r from-[#feb303] to-[#8e07ef] opacity-40 [mask-image:radial-gradient(farthest-side_at_top,white,transparent)] dark:from-[#36b49f]/30 dark:to-[#DBFF75]/30 dark:opacity-100"></div>
            <svg
              viewBox="0 0 1113 440"
              aria-hidden="true"
              className="absolute left-1/2 top-0 ml-[-19rem] w-[69.5625rem] fill-white blur-[30px] dark:hidden"
            >
              <path d="M.016 439.5s-9.5-300 434-300S882.516 20 882.516 20V0h230.004v439.5H.016Z"></path>
            </svg>
          </div>
        </div>
        <Outlet />
      </main>
      </div>
    </div>
  );
}
