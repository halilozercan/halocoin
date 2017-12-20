import React, { Component } from 'react';
import {MCardStats, MCardTable} from './components/card.js';
import Blockcount from './widgets/blockcount.js';
import {timestampToDatetime} from './tools.js';
import axios from 'axios';
import Address from './widgets/address.js';
import AppBar from 'material-ui/AppBar';
import Drawer from 'material-ui/Drawer';
import MenuItem from 'material-ui/MenuItem';
import Balance from './widgets/balance.js';
import Home from 'material-ui/svg-icons/action/home';
import Settings from 'material-ui/svg-icons/action/settings';
import Lock from 'material-ui/svg-icons/action/lock';
import Paper from 'material-ui/Paper';

const bottomBarStyle = {
  position: 'absolute', 
  bottom: 0, 
  width: '100%',
  padding: 16
};

class MainPage extends Component {

  constructor(props){
    super(props);
    this.state = {
      'default_wallet': null,
      'drawer_open': false
    }
  }

  componentDidMount() {
    this.getDefaultWallet();
  }

  drawerToggle = () => this.setState((state) => {
    state.drawer_open = !state.drawer_open;
    return state;
  });

  getDefaultWallet = () => {
    axios.get("/info_wallet").then((response) => {
      let data = response.data;
      if(data.hasOwnProperty('address')) {
        this.setState({default_wallet:data});
      }
      else {
        this.setState({default_wallet:null});
      }
    });
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
    return (
      <div>
        <AppBar
          title="Coinami"
          iconClassNameRight="muidocs-icon-navigation-expand-more"
          onLeftIconButtonClick={this.drawerToggle}
        />
        <Drawer open={this.state.drawer_open} docked={false} onRequestChange={(drawer_open) => this.setState({drawer_open})}>
          <MenuItem leftIcon={<Home />}>Home</MenuItem>
          <MenuItem leftIcon={<Settings />}>Mining</MenuItem>
          <MenuItem leftIcon={<Lock />} onClick={this.onLogout}>Logout</MenuItem>
        </Drawer>
        <div className="container-fluid" style={{marginTop:16}}>
          <div className="row">
            <Balance wallet={this.state.default_wallet} notify={this.props.notify} />
          </div>
          <div className="row">
            <Address wallet={this.state.default_wallet} notify={this.props.notify} />
          </div>
          <div className="row">
            
          </div>
        </div>
        <Paper style={bottomBarStyle}  zDepth={1}>
          Blockcount: 225-3569
        </Paper>
      </div>
    );
  }
}

export default MainPage;
