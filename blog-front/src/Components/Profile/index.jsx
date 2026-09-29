import { Link } from "react-router-dom";
import { FaGithub, FaLinkedinIn } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";
import profileLogo from "../../assets/logo.png";
import Card from "../UI/Card";
import "./style.css";

function Profile() {
  return (
    <Card>
      <section className="profileCard" aria-labelledby="profile-name">
        <div className="profileLogoFrame">
          <img src={profileLogo} alt="SECOVATE200 Bug Hunter 로고" />
        </div>

        <p className="profileRole">BUG HUNTER</p>
        <h2 id="profile-name">SECOVATE200</h2>
        <p className="profileBio">
          보안 취약점과 개발 과정에서 배운 내용을 기록합니다.
        </p>

        <div className="profileSocials" aria-label="SNS 링크">
          <button type="button" aria-label="GitHub" title="GitHub">
            <FaGithub />
          </button>
          <button type="button" aria-label="LinkedIn" title="LinkedIn">
            <FaLinkedinIn />
          </button>
          <button type="button" aria-label="X" title="X">
            <FaXTwitter />
          </button>
        </div>

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
