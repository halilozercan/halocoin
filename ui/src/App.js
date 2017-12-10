import React, { Component } from 'react';
import MSidebar from './components/sidebar.js';
import MNavbar from './components/navbar.js';
import MainPage from './MainPage.js';
import WalletManagement from './WalletManagement.js';
import NotificationSystem from 'react-notification-system';
import io from 'socket.io-client';

class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      "page": "Dashboard"
    }
    this.pageChanged = this.pageChanged.bind(this);
    this.notify = this.notify.bind(this);
    this.pagesIcons = {
      "Dashboard": "dashboard",
      "Wallet Manager": "explore"
    }
    this.socket = io();
    this.socket.on('new_block', (socket) => {
      if(this.state.page == "Dashboard")
        this.mainPage.updateBlocks();
    });

    this.socket.on('peer_update', (socket) => {
      if(this.state.page == "Dashboard")
        this.mainPage.updatePeers();
    });

    this.socket.on('new_tx_in_pool', (socket) => {
      if(this.state.page == "Dashboard")
        this.mainPage.updateTxs();
    });
  }

  componentDidMount() {
    this._notificationSystem = this.refs.notificationSystem;
  }

  pageChanged(newPage) {
    this.setState({"page": newPage});
  }

  notify(message, type, pos='bc') {
    this._notificationSystem.addNotification({
      message: message,
      level: type,
      position: pos
    });
  }

  render() {
    let page = <div />;
    if(this.state.page == "Dashboard") {
      page = <MainPage ref={(input)=>{this.mainPage = input;}} notify={this.notify} />;
    }
    else if(this.state.page == "Wallet Manager") {
      page = <WalletManagement notify={this.notify} />;
    }
    return (
      <div className="wrapper">
        <MSidebar pageChange={this.pageChanged} currentPage={this.state.page} pages={this.pagesIcons}/>
        <div className="main-panel">
          <MNavbar />
          <div className="content">
            {page}
          </div>
        </div>
        <NotificationSystem ref="notificationSystem" />
      </div>
    );
  }
}

export default App;
