import React, { Component } from 'react';
import MSidebar from './components/sidebar.js';
import MNavbar from './components/navbar.js';
import MainPage from './MainPage.js';
import WalletManagement from './WalletManagement.js';
import './App.css';
import NotificationSystem from 'react-notification-system';

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      "page": "Dasboard"
    }
    this.pageChanged = this.pageChanged.bind(this);
    this.notify = this.notify.bind(this);
    this.pagesList = {
      "Dasboard": <MainPage notify={this.notify}/>,
      "Wallet Manager": <WalletManagement notify={this.notify}/>
    }
    this.pagesIcons = {
      "Dasboard": "dashboard",
      "Wallet Manager": "explore"
    }
  }

  componentDidMount() {
    this._notificationSystem = this.refs.notificationSystem;
  }

  pageChanged(newPage) {
    this.setState({"page": newPage});
  }

  notify(message, type) {
    this._notificationSystem.addNotification({
      message: message,
      level: type,
      position: 'bc'
    });
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
        <NotificationSystem ref="notificationSystem" />
      </div>
    );
  }
}

export default App;
