import React, { Component } from 'react';
import MSidebar from './components/sidebar.js';
import MNavbar from './components/navbar.js';
import MainPage from './MainPage.js';
import WalletManagement from './WalletManagement.js';
import './App.css';

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      "page": "Dasboard"
    }
    this.pageChanged = this.pageChanged.bind(this);
    this.pagesList = {
      "Dasboard": <MainPage />,
      "Wallet Manager": <WalletManagement />
    }
    this.pagesIcons = {
      "Dasboard": "dashboard",
      "Wallet Manager": "explore"
    }
  }

  pageChanged(newPage) {
    this.setState({"page": newPage});
  }

  render() {
    return (
      <div className="wrapper">
        <MSidebar pageChange={this.pageChanged} currentPage={this.state.page} pages={this.pagesIcons}/>
        <div className="main-panel">
          <MNavbar />
          <div className="content">
            {this.pagesList[this.state.page]}
          </div>
        </div>
      </div>
    );
  }
}

export default App;
