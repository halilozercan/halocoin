import React, { Component } from 'react';
import axios from 'axios';
import WalletManagement from './WalletManagement.js';
import Mining from './Mining.js';
import AppBar from 'material-ui/AppBar';
import Drawer from 'material-ui/Drawer';
import MenuItem from 'material-ui/MenuItem';
import Home from 'material-ui/svg-icons/action/home';
import Settings from 'material-ui/svg-icons/action/settings';
import Lock from 'material-ui/svg-icons/action/lock';
import Blockcount from './widgets/blockcount.js';

class MainPage extends Component {

  constructor(props){
    super(props);
    this.state = {
      'drawer_open': false,
      'page': 'main'
    }
  }

  drawerToggle = () => this.setState((state) => {
    state.drawer_open = !state.drawer_open;
    return state;
  });

  changePage = (newPage) => {
    this.setState({
      page: newPage,
      drawer_open: false
    })
  }

  onLogout = () => {
    let data = new FormData()
    data.append('delete', true);

    axios.post('/set_default_wallet', data).then((response) => {
      
    }).catch((error) => {
      this.props.notify('Failed to logout', 'error');
    })
  }

  render() {
    let currentPage = <div />
    if(this.state.page === 'main') {
      console.log('Account: ' + this.state.account);
      currentPage = <WalletManagement notify={this.props.notify} 
                                      wallet={this.props.wallet} 
                                      account={this.props.account}
                                      socket={this.props.socket} />;
    }
    else if(this.state.page === 'mining') {
      currentPage = <Mining notify={this.props.notify} 
                            wallet={this.props.wallet} 
                            account={this.props.account}
                            socket={this.props.socket} />
    }
    let title = "Halocoin";
    if(this.props.wallet !== null) {
      title += " - " + this.props.wallet.name;
    }
    return (
      <div>
        <AppBar
          title={title}
          iconClassNameRight="muidocs-icon-navigation-expand-more"
          onLeftIconButtonClick={this.drawerToggle}
        />
        <Drawer open={this.state.drawer_open} docked={false} onRequestChange={(drawer_open) => this.setState({drawer_open})}>
          <MenuItem leftIcon={<Home />} onClick={() => {this.changePage('main')}} >Home</MenuItem>
          <MenuItem leftIcon={<Settings />} onClick={() => {this.changePage('mining')}}>Mining</MenuItem>
          <MenuItem leftIcon={<Lock />} onClick={this.onLogout}>Logout</MenuItem>
        </Drawer>
        {currentPage}
        <Blockcount socket={this.props.socket} notify={this.props.notify}/>
      </div>
    );
  }
}

export default MainPage;
