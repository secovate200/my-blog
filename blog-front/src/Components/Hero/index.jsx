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
