import React, { Component } from 'react';
import Balance from './widgets/balance.js';
import Address from './widgets/address.js';
import Send from './widgets/send.js';
import Stake from './widgets/stake.js';

class WalletManagement extends Component {

  render() {
    return (
      <div className="container-fluid" style={{marginTop:16, marginBottom:64}}>
        <div className="row">
          <div className="col-lg-6 col-md-6 col-sm-6">
            <Balance account={this.props.account} notify={this.props.notify} />
          </div>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <Address account={this.props.account} notify={this.props.notify} />
          </div>
        </div>
        <div className="row" style={{marginTop:"16px"}}>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <Send notify={this.props.notify} refresh={this.forceUpdate}/>
          </div>
          <div className="col-lg-6 col-md-6 col-sm-6">
            <Stake socket={this.props.socket} account={this.props.account} notify={this.props.notify}/>
          </div>
        </div>
      </div>
    );
  }
}

export default WalletManagement;