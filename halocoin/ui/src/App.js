import React, { Component } from 'react';
import MSidebar from './components/sidebar.js';
import MNavbar from './components/navbar.js';
import MainPage from './MainPage.js';
import './App.css';

class App extends Component {
  render() {
    return (
      <div className="wrapper">
        <MSidebar />
        <div className="main-panel">
          <MNavbar />
          <div className="content">
            <MainPage />
          </div>
        </div>
      </div>
    );
  }
}

export default App;
