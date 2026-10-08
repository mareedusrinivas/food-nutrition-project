import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';

/**
 * MainLayout — shared page chrome (header + footer) that both pages use.
 * The rotating animated background lives on <body> in index.css, exactly as
 * in the original style.css.
 */
export default function MainLayout({ title, subtitle, children }) {
  return (
    <>
      <Header title={title} subtitle={subtitle} />
      <main>{children}</main>
      <Footer />
    </>
  );
}
