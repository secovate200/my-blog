/** 홈 화면의 핵심 목적과 다음 탐색 행동을 짧게 안내하는 소개 영역입니다. */
import "./style.css";
import Card from "../UI/Card";
import Logo from "../Logo";
function Hero() {
  return (
    <div className="hero">
      <Card>
        <div className="heroContent">
          <Logo />
        </div>
      </Card>
    </div>
  );
}
export default Hero;
