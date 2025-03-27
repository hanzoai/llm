import Link from "next/link";
import React, { useState, useEffect } from "react";
import type { MenuProps } from "antd";
import { Dropdown } from "antd";
import { Organization } from "@/components/networking";
import { defaultOrg } from "@/components/common_components/default_org";
import {
  UserOutlined,
  LogoutOutlined
} from '@ant-design/icons';
import { clearTokenCookies } from "@/utils/cookieUtils";
import { fetchProxySettings } from "@/utils/proxyUtils";

interface NavbarProps {
  userID: string | null;
  userEmail: string | null;
  userRole: string | null;
  premiumUser: boolean;
  setProxySettings: React.Dispatch<React.SetStateAction<any>>;
  proxySettings: any;
  accessToken: string | null;
}

const Navbar: React.FC<NavbarProps> = ({
  userID,
  userEmail,
  userRole,
  premiumUser,
  proxySettings,
  setProxySettings,
  accessToken,
}) => {
  const isLocal = process.env.NODE_ENV === "development";
  const imageUrl = isLocal ? "http://localhost:4000/logo.png" : "/logo.png";
  const [logoutUrl, setLogoutUrl] = useState("");

  useEffect(() => {
    const initializeProxySettings = async () => {
      if (accessToken) {
        const settings = await fetchProxySettings(accessToken);
        console.log("response from fetchProxySettings", settings);
        if (settings) {
          setProxySettings(settings);
        }
      }
    };

    initializeProxySettings();
  }, [accessToken]);

  useEffect(() => {
    setLogoutUrl(proxySettings?.PROXY_LOGOUT_URL || "");
  }, [proxySettings]);

  const handleLogout = () => {
    clearTokenCookies();
    window.location.href = logoutUrl;
  };

  const userItems: MenuProps["items"] = [
    {
      key: "1",
      label: (
        <div className="py-1">
          <p className="text-sm text-gray-300">Role: {userRole}</p>
          <p className="text-sm text-gray-300">Email: {userEmail || "Unknown"}</p>
          <p className="text-sm text-gray-300"><UserOutlined /> {userID}</p>
          <p className="text-sm text-gray-300">Premium User: {String(premiumUser)}</p>
        </div>
      ),
    },
    {
      key: "2",
      label: <p className="text-sm text-gray-300 hover:text-white" onClick={handleLogout}><LogoutOutlined /> Logout</p>,
    }
  ];


  return (
    <nav className="bg-black border-b border-gray-800 sticky top-0 z-10">
      <div className="w-full">
        <div className="flex items-center h-12 px-4">
          {/* Left side with correct logo positioning */}
          <div className="flex items-center flex-shrink-0">
            <Link href="/" className="flex items-center">
              <img
                src={imageUrl}
                alt="Hanzo AI"
                className="h-8 w-auto"
              />
            </Link>
          </div>

          {/* Right side nav items */}
          <div className="flex items-center space-x-5 ml-auto">
            <a
              href="https://docs.hanzo.ai/docs/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] text-white hover:text-white hover:bg-opacity-10 hover:bg-white transition-colors px-4 py-2 border border-white rounded"
            >
              Docs
            </a>
            
            <a
              href="https://cloud.hanzo.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] text-white hover:text-white hover:bg-opacity-10 hover:bg-white transition-colors px-4 py-2 border border-white rounded"
            >
              Console
            </a>
            
            <a
              href="https://cloud.hanzo.ai/signup"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] text-black hover:text-black bg-white hover:bg-gray-100 transition-colors px-4 py-2 rounded font-medium"
            >
              Sign Up
            </a>

            <Dropdown
              menu={{
                items: userItems,
                style: {
                  padding: '4px',
                  marginTop: '4px',
                  backgroundColor: '#111',
                  border: '1px solid #333',
                  color: '#fff'
                }
              }}
            >
              <button className="inline-flex items-center text-[13px] text-white hover:text-white transition-colors ml-4">
                User
                <svg
                  className="ml-1 w-4 h-4 text-gray-200"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </Dropdown>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
