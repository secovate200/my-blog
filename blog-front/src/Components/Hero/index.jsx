import "./style.css";
import Card from "../UI/Card";
import Logo from "../Logo";
function Hero() {
  return (
    <div className="hero">
      <Card>
        <div style={{ padding: "50px 0" }}>
          <Logo />
        </div>
      </Card>
    </div>
  );
}
export default Hero;
