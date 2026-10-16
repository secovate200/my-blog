/** DB에서 관리하는 운영자 소개와 SNS 링크를 사이드 영역에 표시합니다. */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FaFacebookF, FaGithub, FaInstagram } from "react-icons/fa";
import profileLogo from "../../assets/logo.png";
import { getSiteProfile } from "../../api/profile";
import Card from "../UI/Card";
import "./style.css";

const DEFAULT_PROFILE = {
  name: "SECOVATE200",
  role: "BUG HUNTER",
  bio: "보안 취약점과 개발 과정에서 배운 내용을 기록합니다.",
  logo_url: null,
  instagram_url: "",
  github_url: "",
  facebook_url: "",
};

function Profile() {
  const [profile, setProfile] = useState(DEFAULT_PROFILE);
  const [logoFailed, setLogoFailed] = useState(false);

  useEffect(() => {
    let active = true;
    getSiteProfile()
      .then((data) => {
        if (active) setProfile({ ...DEFAULT_PROFILE, ...data });
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const socialLinks = [
    ["Instagram", profile.instagram_url, FaInstagram],
    ["GitHub", profile.github_url, FaGithub],
    ["Facebook", profile.facebook_url, FaFacebookF],
  ].filter(([, url]) => url);

  return (
    <Card>
      <section className="profileCard" aria-labelledby="profile-name">
        <div className="profileLogoFrame">
          <img
            src={profile.logo_url && !logoFailed ? profile.logo_url : profileLogo}
            alt={`${profile.name} 로고`}
            onError={() => setLogoFailed(true)}
          />
        </div>
        {profile.role && <p className="profileRole">{profile.role}</p>}
        <h2 id="profile-name">{profile.name}</h2>
        {profile.bio && <p className="profileBio">{profile.bio}</p>}
        {socialLinks.length > 0 && (
          <div className="profileSocials" aria-label="SNS 링크">
            {socialLinks.map(([label, url, Icon]) => (
              <a key={label} href={url} target="_blank" rel="noreferrer noopener" aria-label={label} title={label}>
                <Icon />
              </a>
            ))}
          </div>
        )}
        <div className="profileDivider" aria-hidden="true" />
        <nav className="profileLinks" aria-label="프로필 바로가기">
          <Link to="/category">Category</Link>
          <Link to="/project">Project</Link>
          <Link to="/contact">Contact</Link>
        </nav>
      </section>
    </Card>
  );
}

export default Profile;
