import { NavLink } from "react-router-dom";
// navbar-dark bg-dark
const AdminNavBar = () => {
    return (
        <nav className="navbar navbar navbar-height" style={{ borderBottom: '2px solid #ddd' }}>
            <div className="container">
                <ul id="nav2" className="nav container-fluid justify-content-center ">
                    <li className="nav-item me-5">
                    <NavLink 
                        activeClassName = "active"
                        className="btn btn-primary" 
                        aria-current="page" 
                        to="/"
                        style={{ 
                            textDecoration: 'none', 
                            fontFamily: 'SansM', 
                            fontSize:'30px',
                            boxShadow: '0px 4px 10px rgba(0,0,0,5)' 
                        }}>
                        HOME
                    </NavLink>
                    </li>
                    <li className="nav-item me-5">
                    <NavLink 
                        activeClassName = "active"
                        className="btn btn-danger" 
                        aria-current="page" 
                        to="/admin/menu/reg"
                        style={{ 
                            textDecoration: 'none', 
                            fontFamily: 'SansM', 
                            fontSize:'30px',
                            boxShadow: '0px 4px 10px rgba(0,0,0,5)' 
                        }}>
                        메뉴 등록</NavLink>
                    </li>
                    <li className="nav-item">
                    <NavLink
                        activeClassName = "active"
                        className="btn btn-dark"
                        to = "/admin/changepw"
                        aria-current="page" 
                        style={{ 
                            textDecoration: 'none', 
                            fontFamily: 'SansM', 
                            fontSize:'20px',
                            boxShadow: '0px 4px 10px rgba(0,0,0,5)' 
                        }}>
                        관리자 비밀번호 수정
                    </NavLink>
                    </li>
                    <li className="nav-item me-5 ms-auto"> {/* ms-auto 클래스 추가 */}
                    {/* <img src={'/img/menu_reg.png'} alt="메뉴 등록" height="110" width="300"/> */}
                    <img src={require('../img/Logo.png')} alt="logo" height="100" width="300"/>
                    </li>
                </ul> 
            </div>
        </nav>
    );
    
};

export default AdminNavBar;