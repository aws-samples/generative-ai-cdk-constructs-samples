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
import Avatar from "@/components/Avatar";
import { Link, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { languages } from "@/lib/i18n";
import { useEffect, useState, useRef } from "react";
// import { getGravatarUrl } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuPortal,
  DropdownMenuSubContent,
} from "@/components/ui/dropdown-menu";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { Menu, Globe, ChevronDown, LogOut as LogoutIcon, FileText, Settings } from "lucide-react";
import { ImportContractType } from "@/components/ImportContractType";

import Logo from "@/assets/aws.svg";

export default function Navbar() {
  const { i18n, t } = useTranslation();
  const { user, signOut } = useAuthenticator((context) => [context.user]);

  const displayName = user?.username || "Guest";
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navDrawerOpen, setNavDrawerOpen] = useState(false);
  const isDesktop = useIsDesktop("(min-width: 768px)");
  const importTriggerRef = useRef<HTMLButtonElement>(null);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate("/");
    } catch (error) {
      console.error(error);
    }
  };

  const handleImportComplete = (contractTypeId: string) => {
    // Close the navigation drawer
    setNavDrawerOpen(false);
    // Navigate to the guidelines management for the new contract type
    navigate(`/contract-types/${encodeURIComponent(contractTypeId)}/guidelines`);
  };

  const env = import.meta.env;

  return (
    <nav className="mb-1 flex w-full items-center justify-between border-b bg-white p-3 shadow-sm">
      {/* Burger Menu */}
      <Drawer direction="left" open={navDrawerOpen} onOpenChange={setNavDrawerOpen}>
        <DrawerTrigger asChild>
          <button
            className="rounded p-2 hover:bg-neutral-100"
            aria-label={t("nav.menu.openNavigation")}
          >
            <Menu className="h-5 w-5" />
          </button>
        </DrawerTrigger>
        <DrawerContent className="w-64">
          <DrawerHeader>
            <DrawerTitle>{t("nav.menu.navigation")}</DrawerTitle>
            <DrawerDescription>
              {t("nav.menu.navigationDescription")}
            </DrawerDescription>
          </DrawerHeader>
          <div className="flex-1 px-4 py-2">
            <div className="space-y-2">
              <Link
                to="/"
                className="flex items-center gap-3 rounded px-3 py-2 text-sm hover:bg-neutral-100"
                onClick={() => setNavDrawerOpen(false)}
              >
                <FileText className="h-4 w-4" />
                <span>{t("nav.menu.complianceAnalysis")}</span>
              </Link>
              <Link
                to="/contract-types"
                className="flex items-center gap-3 rounded px-3 py-2 text-sm hover:bg-neutral-100"
                onClick={() => setNavDrawerOpen(false)}
              >
                <Settings className="h-4 w-4" />
                <span>{t("nav.menu.contractTypes")}</span>
              </Link>
            </div>
          </div>
        </DrawerContent>
      </Drawer>

      {/* App Name with AWS Logo */}
      <Link to="/">
        <div className="flex items-center text-slate-900 hover:text-slate-700">
          {env.VITE_APP_LOGO_URL ? (
            <img className="mr-2 h-6 w-6" src={env.VITE_APP_LOGO_URL} alt="Logo" />
          ) : (
            <img src={Logo} alt="AWS" className="mr-2 h-6 w-6" />
          )}
          <h1 className="text-md font-bold leading-8">{env.VITE_APP_NAME}</h1>
        </div>
      </Link>

      <div className="flex items-center gap-2">
        {isDesktop ? (
          <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
            <DropdownMenuTrigger asChild>
              <div className="flex items-center">
                <Avatar size={"small"} avatarType="human" />
                <ChevronDown className="ml-1 h-4 w-4 text-muted-foreground" />
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end">
              <DropdownMenuLabel>
                {displayName
                  ? t("nav.user.loggedInAs", { username: displayName })
                  : t("nav.language.label")}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />

              <DropdownMenuSub>
                <DropdownMenuSubTrigger className="cursor-pointer">
                  <Globe className="mr-2 h-4 w-4" />
                  <span>{t("nav.language.changeLanguage")}</span>
                </DropdownMenuSubTrigger>
                <DropdownMenuPortal>
                  <DropdownMenuSubContent className="w-48">
                    {languages.map((lang) => (
                      <DropdownMenuItem
                        key={lang.code}
                        className={
                          lang.code === i18n.language
                            ? "bg-primary text-primary-foreground"
                            : undefined
                        }
                        onClick={() => i18n.changeLanguage(lang.code)}
                      >
                        <span className="mr-2">{lang.flag}</span>
                        <span className="text-sm">{lang.nativeName}</span>
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuSubContent>
                </DropdownMenuPortal>
              </DropdownMenuSub>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="cursor-pointer"
                onClick={handleSignOut}
              >
                <LogoutIcon className="mr-2 h-4 w-4" />
                <span>{t("nav.user.logout")}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Drawer open={menuOpen} onOpenChange={setMenuOpen}>
            <DrawerTrigger asChild>
              <button
                className="rounded p-2 hover:bg-neutral-100"
                aria-label={t("nav.menu.toggleMenu")}
              >
                <Menu className="h-5 w-5" />
              </button>
            </DrawerTrigger>
            <DrawerContent className="h-[85vh]">
              <DrawerHeader>
                <DrawerTitle>{env.VITE_APP_NAME}</DrawerTitle>
                <DrawerDescription>
                  {t("nav.language.changeLanguage")}
                </DrawerDescription>
              </DrawerHeader>

              <div className="flex-1 overflow-y-auto px-4 py-2">
                <div className="grid grid-cols-2 gap-2">
                  {languages.map((lang) => (
                    <button
                      key={lang.code}
                      className={`flex items-center justify-start gap-2 rounded border px-3 py-2 text-sm ${lang.code === i18n.language ? "bg-neutral-100" : ""
                        }`}
                      onClick={() => {
                        i18n.changeLanguage(lang.code);
                        setMenuOpen(false);
                      }}
                    >
                      <span>{lang.flag}</span>
                      <span>{lang.nativeName}</span>
                    </button>
                  ))}
                </div>
              </div>
              <DrawerFooter className="flex flex-col gap-2 space-y-0">
                <button
                  className="w-full justify-start rounded border px-3 py-2 text-left text-sm"
                  onClick={handleSignOut}
                >
                  <span className="mr-2 inline-flex">
                    <LogoutIcon className="h-4 w-4" />
                  </span>
                  <span>{t("nav.user.logout")}</span>
                </button>
              </DrawerFooter>
            </DrawerContent>
          </Drawer>
        )}
      </div>

      {/* Hidden Import Contract Type Dialog */}
      <ImportContractType
        onImportComplete={handleImportComplete}
        trigger={
          <button ref={importTriggerRef} style={{ display: 'none' }}>
            Hidden Import Trigger
          </button>
        }
      />
    </nav>
  );
}

function useIsDesktop(query: string) {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    if (mql.addEventListener) mql.addEventListener("change", onChange);
    else mql.addListener(onChange);
    setMatches(mql.matches);
    return () => {
      if (mql.removeEventListener) mql.removeEventListener("change", onChange);
      else mql.removeListener(onChange);
    };
  }, [query]);

  return matches;
}
