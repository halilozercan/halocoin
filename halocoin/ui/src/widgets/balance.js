import React, { Component } from 'react';
import {MCardStats, MCardTable} from '../components/card.js';
import $ from "jquery";

class Balance extends Component {
  render() {
    return (
      <div className="col-lg-3 col-md-6 col-sm-6">
        <MCardStats color="green" header_icon="info_outline" title="Balance"
         content={this.props.balance}
         footer_icon="local_offer" alt_text={"Belongs to: " + this.props.name}/>
      </div>
    );
  }
}

export default Balance;