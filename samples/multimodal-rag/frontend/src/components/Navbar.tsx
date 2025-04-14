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

import { useAuthenticator } from "@aws-amplify/ui-react";
import { IconLogout, IconBook2 as Icon } from "@tabler/icons-react";
import Avatar from "@/components/Avatar";
import { Link, useNavigate } from "react-router-dom";

import Logo from "@/assets/aws.svg";

export default function Navbar() {
  const { signOut } = useAuthenticator((context) => [context.user]);
  const navigate = useNavigate();

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate("/");
    } catch (error) {
      console.error(error);
    }
  };

  const env = import.meta.env;

  return (
    <nav className="mb-1 flex w-full items-center justify-between border-b bg-white p-3 shadow-sm">
      <Link to="/">
        <img src={Logo} alt="AWS" />
      </Link>
      <Link to="/">
        <div className="flex items-center text-slate-900 hover:text-slate-700">
          <Icon className="mr-1" />
          <h1 className="text-md font-bold leading-8">{env.VITE_APP_NAME}</h1>
        </div>
      </Link>
      
      {env.VITE_APP_LOGO_URL !== "" && (
        <img className="md-hidden h-8" src={env.VITE_APP_LOGO_URL} />
      )}

      <div className="flex">
        <Avatar size="small" avatarType="user" />

        <button
          onClick={handleSignOut}
          className="ml-4 text-sm text-slate-800 hover:text-slate-600"
        >
          <span className="font-bold">
            <IconLogout className="text-slate-900" />
          </span>
        </button>
      </div>
    </nav>
  );
}
