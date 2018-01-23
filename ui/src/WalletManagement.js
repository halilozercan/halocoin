import React, { Component } from 'react';
import Balance from './widgets/balance.js';
import Address from './widgets/address.js';
import Send from './widgets/send.js';

class WalletManagement extends Component {

  render() {
    return (
      <div className="container-fluid" style={{marginTop:16, marginBottom:64}}>
        <div className="row">
          <div className="col-lg-3 col-md-6 col-sm-6">
            <Balance wallet={this.props.default_wallet} notify={this.props.notify} />
          </div>
          <div className="col-lg-3 col-md-6 col-sm-6">
            <Address wallet={this.props.default_wallet} notify={this.props.notify} />
          </div>
        </div>
        <div className="row">
          <Send notify={this.props.notify} refresh={this.forceUpdate}/>
        </div>
      </div>
    );
  }
}

export default WalletManagement;